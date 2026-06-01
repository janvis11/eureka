"""
Structural RAG Engine — PageIndex-Inspired Implementation.

The core idea from PageIndex:
  Instead of breaking a document into arbitrary word-chunks and doing
  "similarity retrieval" (vibe search), treat every document like a book:
    1. INDEXING: Extract the document's natural section hierarchy (like a TOC)
    2. RETRIEVAL: Give the LLM the section tree → LLM REASONS about which
       sections likely contain the answer → fetch those exact sections
    3. ANSWER: Generate answer from fetched sections + show evidence breadcrumbs

Why this beats flat FAISS/vector search:
  - Preserves document structure (no split tables, equations, paragraphs)
  - LLM reasoning > cosine similarity matching
  - Every answer has a traceable section path, not just a score
  - Works even for documents with complex structure (papers, reports, patents)
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple

from app.config import get_settings
from app.services.model_gateway.base import ChatMessage, GenerationRequest

logger = logging.getLogger(__name__)
settings = get_settings()


# ---------------------------------------------------------------------------
# Data Structures
# ---------------------------------------------------------------------------

@dataclass
class SectionNode:
    """A single section in the document hierarchy."""
    section_id: str          # Unique ID like "doc_1_s_2_1"
    title: str               # Section heading (e.g., "2.1 Methodology")
    level: int               # 1=chapter, 2=section, 3=subsection, 4=paragraph
    text: str                # Full text content of this section
    page_start: int = 0
    page_end: int = 0
    children: List[str] = field(default_factory=list)   # Child section IDs
    parent: Optional[str] = None
    char_count: int = 0


@dataclass
class SectionTree:
    """The complete hierarchical section structure of a document."""
    doc_id: str
    title: str
    sections: Dict[str, SectionNode] = field(default_factory=dict)
    root_ids: List[str] = field(default_factory=list)   # Top-level sections
    total_sections: int = 0

    def to_toc_string(self, max_sections: int = 60) -> str:
        """
        Render a Table of Contents string for LLM navigation.
        The LLM reads this and decides which section IDs to fetch.
        """
        lines = [f"DOCUMENT: {self.title}", "=" * 40, "TABLE OF CONTENTS:"]
        count = 0

        def render(section_id: str, indent: int = 0):
            nonlocal count
            if count >= max_sections or section_id not in self.sections:
                return
            node = self.sections[section_id]
            prefix = "  " * indent + ("├─ " if indent > 0 else "")
            lines.append(
                f"{prefix}[{node.section_id}] {node.title} "
                f"(~{node.char_count} chars)"
            )
            count += 1
            for child_id in node.children[:8]:  # Limit children per node
                render(child_id, indent + 1)

        for root_id in self.root_ids[:20]:
            render(root_id)

        return "\n".join(lines)

    def get_section_texts(self, section_ids: List[str]) -> List[Dict[str, Any]]:
        """Fetch text from specified section IDs."""
        results = []
        for sid in section_ids:
            if sid in self.sections:
                node = self.sections[sid]
                results.append({
                    "section_id": sid,
                    "title": node.title,
                    "level": node.level,
                    "text": node.text,
                    "breadcrumb": self._build_breadcrumb(sid),
                })
        return results

    def _build_breadcrumb(self, section_id: str) -> str:
        """Build a breadcrumb path like: 'Introduction → 1.2 Background → 1.2.3 Prior Work'"""
        path = []
        current = section_id
        while current and current in self.sections:
            node = self.sections[current]
            path.insert(0, node.title)
            current = node.parent
        return " → ".join(path)


@dataclass
class StructuralRetrievalResult:
    """Result from structural retrieval with full provenance."""
    query: str
    sections: List[Dict[str, Any]]      # Retrieved sections with breadcrumbs
    reasoning_trace: str                 # LLM's section selection reasoning
    navigation_path: List[str]           # Section IDs visited
    total_chars: int = 0


# ---------------------------------------------------------------------------
# Document Section Index (stores trees in memory, can persist to disk)
# ---------------------------------------------------------------------------

class DocumentSectionIndex:
    """
    In-memory store of section trees for all uploaded documents.
    Serializes to JSON for persistence between restarts.
    """

    def __init__(self, persistence_dir: str = "./data/section_index"):
        import os
        self.persistence_dir = persistence_dir
        os.makedirs(persistence_dir, exist_ok=True)
        self._trees: Dict[str, SectionTree] = {}
        self._load_all()

    def store_tree(self, tree: SectionTree) -> None:
        """Store a section tree and persist to disk."""
        self._trees[tree.doc_id] = tree
        self._persist_tree(tree)

    def get_tree(self, doc_id: str) -> Optional[SectionTree]:
        """Retrieve a section tree by document ID."""
        return self._trees.get(doc_id)

    def get_all_tocs(self) -> List[Dict[str, str]]:
        """Get TOC summaries for all documents."""
        return [
            {"doc_id": tree.doc_id, "title": tree.title, "sections": tree.total_sections}
            for tree in self._trees.values()
        ]

    def delete_tree(self, doc_id: str) -> None:
        """Remove a document tree."""
        self._trees.pop(doc_id, None)
        import os
        path = self._tree_path(doc_id)
        if os.path.exists(path):
            os.remove(path)

    def _tree_path(self, doc_id: str) -> str:
        import os
        safe_id = doc_id.replace("/", "_").replace("\\", "_")
        return os.path.join(self.persistence_dir, f"{safe_id}.json")

    def _persist_tree(self, tree: SectionTree) -> None:
        try:
            path = self._tree_path(tree.doc_id)
            with open(path, "w", encoding="utf-8") as f:
                data = {
                    "doc_id": tree.doc_id,
                    "title": tree.title,
                    "root_ids": tree.root_ids,
                    "total_sections": tree.total_sections,
                    "sections": {
                        sid: asdict(node) for sid, node in tree.sections.items()
                    },
                }
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to persist section tree for {tree.doc_id}: {e}")

    def _load_all(self) -> None:
        import os
        import glob
        pattern = os.path.join(self.persistence_dir, "*.json")
        for path in glob.glob(pattern):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                tree = SectionTree(
                    doc_id=data["doc_id"],
                    title=data["title"],
                    root_ids=data.get("root_ids", []),
                    total_sections=data.get("total_sections", 0),
                )
                for sid, sdata in data.get("sections", {}).items():
                    tree.sections[sid] = SectionNode(**sdata)

                self._trees[tree.doc_id] = tree
                logger.info(f"Loaded section tree for {tree.doc_id} ({tree.total_sections} sections)")
            except Exception as e:
                logger.warning(f"Failed to load section tree from {path}: {e}")


# ---------------------------------------------------------------------------
# Structural RAG Engine
# ---------------------------------------------------------------------------

class StructuralRAGEngine:
    """
    PageIndex-inspired RAG engine.

    Retrieval process:
      1. Load the section tree for relevant documents
      2. Send TOC to LLM → LLM selects section IDs
      3. Fetch those sections verbatim
      4. Generate answer with breadcrumb evidence

    This is fundamentally different from vector search:
      - No embeddings for retrieval (LLM reasons structurally)
      - No arbitrary chunking (sections are natural document units)
      - Full provenance (breadcrumb to every source sentence)
    """

    NAVIGATOR_PROMPT = """You are a precise document navigator. You are given a Table of Contents of a research document.

Your task: Read the query and identify which sections MOST LIKELY contain the answer.

QUERY: {query}

{toc}

Instructions:
1. Analyze the TOC carefully
2. Select 2-5 section IDs that are MOST relevant to the query
3. Think step by step about why each section is relevant
4. Prioritize specificity: a focused subsection beats a broad chapter

Respond in this exact JSON format:
{{
  "reasoning": "Why I selected these sections...",
  "selected_sections": ["section_id_1", "section_id_2", "section_id_3"],
  "confidence": 0.0-1.0
}}

JSON only, no other text:"""

    ANSWER_PROMPT = """You are a research analyst. Answer the question using ONLY the provided document sections.

QUESTION: {query}

RETRIEVED SECTIONS:
{sections_text}

Instructions:
1. Answer precisely and concisely using only the provided content
2. Cite which section each fact came from using [Section: title]
3. If the sections don't contain the answer, say "The document doesn't cover this topic in the retrieved sections"
4. Be accurate — don't speculate beyond what's in the text

ANSWER:"""

    def __init__(self, gateway=None):
        self.section_index = DocumentSectionIndex(
            persistence_dir=settings.CHROMADB_PATH + "/section_index"
        )

        if gateway is not None:
            self.gateway = gateway
        else:
            from app.services.shared import get_gateway
            self.gateway = get_gateway()

        logger.info("StructuralRAGEngine initialized (PageIndex-style)")

    # ------------------------------------------------------------------
    # Indexing
    # ------------------------------------------------------------------

    def index_document(self, doc_id: str, tree: SectionTree) -> None:
        """Store a document's section tree for structural retrieval."""
        self.section_index.store_tree(tree)
        logger.info(f"Indexed document {doc_id} with {tree.total_sections} sections")

    def remove_document(self, doc_id: str) -> None:
        """Remove a document from the structural index."""
        self.section_index.delete_tree(doc_id)

    # ------------------------------------------------------------------
    # Retrieval (the PageIndex-inspired step)
    # ------------------------------------------------------------------

    async def retrieve(
        self,
        query: str,
        doc_ids: Optional[List[str]] = None,
        max_sections_per_doc: int = 4,
    ) -> StructuralRetrievalResult:
        """
        Structural retrieval: LLM reads TOC → selects sections → fetch them.

        Args:
            query: The user's question
            doc_ids: Optional list of specific documents to search
            max_sections_per_doc: Max sections to fetch per document

        Returns:
            StructuralRetrievalResult with sections + breadcrumbs + LLM reasoning
        """
        # Determine which documents to search
        if doc_ids:
            trees = [self.section_index.get_tree(d) for d in doc_ids]
            trees = [t for t in trees if t is not None]
        else:
            # Search all indexed documents
            trees = [
                self.section_index.get_tree(info["doc_id"])
                for info in self.section_index.get_all_tocs()
            ]
            trees = [t for t in trees if t is not None]

        if not trees:
            return StructuralRetrievalResult(
                query=query,
                sections=[],
                reasoning_trace="No documents indexed yet.",
                navigation_path=[],
            )

        all_sections = []
        all_reasoning = []
        all_nav_paths = []

        for tree in trees[:5]:  # Limit to 5 docs per query
            sections, reasoning, nav_path = await self._navigate_tree(
                query=query,
                tree=tree,
                max_sections=max_sections_per_doc,
            )
            all_sections.extend(sections)
            all_reasoning.append(f"[{tree.title}]: {reasoning}")
            all_nav_paths.extend(nav_path)

        total_chars = sum(len(s.get("text", "")) for s in all_sections)

        return StructuralRetrievalResult(
            query=query,
            sections=all_sections,
            reasoning_trace="\n".join(all_reasoning),
            navigation_path=all_nav_paths,
            total_chars=total_chars,
        )

    async def _navigate_tree(
        self,
        query: str,
        tree: SectionTree,
        max_sections: int = 4,
    ) -> Tuple[List[Dict[str, Any]], str, List[str]]:
        """Let the LLM navigate the TOC and select relevant sections."""
        toc_string = tree.to_toc_string(max_sections=80)
        prompt = self.NAVIGATOR_PROMPT.format(query=query, toc=toc_string)

        try:
            result = await self.gateway.generate(
                GenerationRequest(
                    messages=[ChatMessage(role="user", content=prompt)],
                    temperature=0.1,     # Low temp for precise navigation
                    max_tokens=400,
                )
            )
            raw = result.text.strip()

            # Parse JSON response
            import re
            json_match = re.search(r"\{.*\}", raw, re.DOTALL)
            if not json_match:
                raise ValueError("No JSON in LLM navigation response")

            nav_data = json.loads(json_match.group())
            selected_ids = nav_data.get("selected_sections", [])[:max_sections]
            reasoning = nav_data.get("reasoning", "")

        except Exception as e:
            logger.warning(f"LLM navigation failed for {tree.doc_id}: {e} — falling back to first sections")
            # Fallback: use first N sections
            selected_ids = tree.root_ids[:max_sections]
            reasoning = f"Fallback: selected top-level sections (navigation error: {e})"

        # Fetch the selected sections
        sections = tree.get_section_texts(selected_ids)

        # Add document metadata to each section
        for section in sections:
            section["document_id"] = tree.doc_id
            section["document_title"] = tree.title

        return sections, reasoning, selected_ids

    # ------------------------------------------------------------------
    # Answer Generation
    # ------------------------------------------------------------------

    async def answer(
        self,
        query: str,
        doc_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Full structural RAG: retrieve sections + generate answer with citations.

        Returns:
            {
                "answer": str,
                "evidence": [{section_id, title, breadcrumb, text}],
                "reasoning_trace": str,
                "navigation_path": [section_ids],
                "method": "structural_rag"
            }
        """
        retrieval = await self.retrieve(query, doc_ids=doc_ids)

        if not retrieval.sections:
            return {
                "answer": "No relevant sections found in the indexed documents.",
                "evidence": [],
                "reasoning_trace": retrieval.reasoning_trace,
                "navigation_path": [],
                "method": "structural_rag",
            }

        # Build context from sections
        sections_text = "\n\n".join([
            f"[Section: {s['title']}]\n"
            f"Path: {s.get('breadcrumb', s['title'])}\n"
            f"Content: {s['text'][:2000]}"
            for s in retrieval.sections
        ])

        prompt = self.ANSWER_PROMPT.format(
            query=query,
            sections_text=sections_text,
        )

        result = await self.gateway.generate(
            GenerationRequest(
                messages=[ChatMessage(role="user", content=prompt)],
                temperature=0.2,
                max_tokens=1200,
            )
        )

        return {
            "answer": result.text,
            "evidence": [
                {
                    "section_id": s["section_id"],
                    "title": s["title"],
                    "breadcrumb": s.get("breadcrumb", s["title"]),
                    "text_preview": s["text"][:300],
                    "document_id": s.get("document_id", ""),
                    "document_title": s.get("document_title", ""),
                }
                for s in retrieval.sections
            ],
            "reasoning_trace": retrieval.reasoning_trace,
            "navigation_path": retrieval.navigation_path,
            "method": "structural_rag",
        }

    def get_stats(self) -> Dict[str, Any]:
        """Return structural index statistics."""
        tocs = self.section_index.get_all_tocs()
        return {
            "indexed_documents": len(tocs),
            "documents": tocs,
            "method": "structural_rag_pageindex_inspired",
        }


# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------

_structural_engine: Optional[StructuralRAGEngine] = None


def get_structural_engine(gateway=None) -> StructuralRAGEngine:
    """Get or create the structural RAG engine singleton."""
    global _structural_engine
    if _structural_engine is None:
        _structural_engine = StructuralRAGEngine(gateway=gateway)
    return _structural_engine
