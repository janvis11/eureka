import os
import re
import PyPDF2
import pdfplumber
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Section Tree data classes (imported by structural_rag_engine)
# ---------------------------------------------------------------------------

class DocumentProcessor:
    """
    Document processor with structure extraction.

    Two modes:
      1. Structure mode (PageIndex-inspired): Extracts section hierarchy
         → builds a SectionTree for structural RAG
      2. Chunk mode (fallback): Traditional overlapping word chunks
         for use with vector-based retrieval when structure is missing
    """

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        # Heading patterns (regex, case-insensitive)
        self._heading_patterns = [
            # Numbered headings: "1.", "1.1", "1.1.1", "2.3.4 Title"
            re.compile(r'^(\d+(?:\.\d+)*)\s+([A-Z][^\n]{3,80})', re.MULTILINE),
            # Roman numerals: "I. Introduction", "II. Methods"
            re.compile(r'^((?:I{1,3}|IV|VI{0,3}|IX|X{1,2}){1,3})\.\s+([A-Z][^\n]{3,60})', re.MULTILINE),
            # Uppercase headings: "INTRODUCTION", "METHODS AND RESULTS"
            re.compile(r'^([A-Z][A-Z\s]{4,50})$', re.MULTILINE),
            # Markdown-style: "## Introduction"
            re.compile(r'^(#{1,4})\s+(.+)$', re.MULTILINE),
        ]

    # ------------------------------------------------------------------
    # Primary: Structure-Aware Extraction
    # ------------------------------------------------------------------

    async def extract_structure(
        self,
        file_path: str,
        doc_id: str,
    ) -> "SectionTree":
        """
        Extract document structure as a hierarchical SectionTree.

        Steps:
          1. Extract full text with page numbers
          2. Detect headings using regex patterns
          3. Build section hierarchy
          4. Assign text to each section node

        Returns a SectionTree suitable for PageIndex-style retrieval.
        """
        from app.services.retrieval.structural_rag_engine import SectionNode, SectionTree

        # Extract text with page info
        pages_text = await self._extract_pages(file_path)
        full_text = "\n".join([p["text"] for p in pages_text])

        # Detect heading positions
        headings = self._detect_headings(full_text)

        # Build section nodes
        sections: Dict[str, SectionNode] = {}
        root_ids: List[str] = []

        # Infer document title from first non-empty lines
        title = self._infer_title(full_text, file_path)

        if not headings:
            # No structure detected → create a single flat section per page
            logger.info(f"No headings detected in {file_path} — using page-based sections")
            for i, page in enumerate(pages_text):
                if not page["text"].strip():
                    continue
                sid = f"{doc_id}_p{i+1}"
                node = SectionNode(
                    section_id=sid,
                    title=f"Page {i + 1}",
                    level=1,
                    text=page["text"],
                    page_start=i + 1,
                    page_end=i + 1,
                    char_count=len(page["text"]),
                )
                sections[sid] = node
                root_ids.append(sid)
        else:
            # Build sections from detected headings
            sections, root_ids = self._build_section_tree(
                doc_id=doc_id,
                full_text=full_text,
                headings=headings,
                pages_text=pages_text,
            )

        tree = SectionTree(
            doc_id=doc_id,
            title=title,
            sections=sections,
            root_ids=root_ids,
            total_sections=len(sections),
        )

        logger.info(
            f"Extracted structure for {doc_id}: "
            f"{len(sections)} sections, {len(root_ids)} top-level"
        )
        return tree

    def _detect_headings(self, text: str) -> List[Dict[str, Any]]:
        """Detect heading positions in the text."""
        headings = []
        seen_positions = set()

        for pattern in self._heading_patterns:
            for match in pattern.finditer(text):
                pos = match.start()
                if pos in seen_positions:
                    continue
                seen_positions.add(pos)

                groups = match.groups()
                if len(groups) >= 2:
                    number = groups[0].strip()
                    title = groups[1].strip() if len(groups) > 1 else groups[0].strip()
                    level = self._infer_level_from_number(number)
                else:
                    number = ""
                    title = groups[0].strip()
                    level = 2

                if len(title) < 3 or len(title) > 120:
                    continue

                headings.append({
                    "pos": pos,
                    "number": number,
                    "title": f"{number} {title}".strip() if number else title,
                    "level": level,
                })

        headings.sort(key=lambda h: h["pos"])
        return headings

    def _infer_level_from_number(self, number: str) -> int:
        """Infer heading level from its numbering (e.g., '2.3.1' → level 3)."""
        if not number:
            return 1
        dots = number.count(".")
        if dots == 0:
            return 1
        elif dots == 1:
            return 2
        elif dots == 2:
            return 3
        else:
            return 4

    def _build_section_tree(
        self,
        doc_id: str,
        full_text: str,
        headings: List[Dict[str, Any]],
        pages_text: List[Dict[str, Any]],
    ) -> Tuple[Dict, List[str]]:
        """Build a tree of SectionNode from detected headings."""
        from app.services.retrieval.structural_rag_engine import SectionNode

        sections: Dict[str, SectionNode] = {}
        root_ids: List[str] = []
        parent_stack: List[Tuple[int, str]] = []  # (level, section_id)

        for i, heading in enumerate(headings):
            sid = f"{doc_id}_s{i}"

            # Extract text: from this heading to next
            start_pos = heading["pos"] + len(heading["title"])
            end_pos = headings[i + 1]["pos"] if i + 1 < len(headings) else len(full_text)
            section_text = full_text[start_pos:end_pos].strip()

            # Cap very long sections
            if len(section_text) > 8000:
                section_text = section_text[:8000] + "\n... [section continues]"

            level = heading["level"]

            # Find parent: pop stack until we find a node with lower level number
            while parent_stack and parent_stack[-1][0] >= level:
                parent_stack.pop()

            parent_id = parent_stack[-1][1] if parent_stack else None

            node = SectionNode(
                section_id=sid,
                title=heading["title"],
                level=level,
                text=section_text,
                char_count=len(section_text),
                parent=parent_id,
            )
            sections[sid] = node

            if parent_id and parent_id in sections:
                sections[parent_id].children.append(sid)
            else:
                root_ids.append(sid)

            parent_stack.append((level, sid))

        return sections, root_ids

    def _infer_title(self, text: str, file_path: str) -> str:
        """Infer document title from text or filename."""
        extracted = self.extract_title_from_text(text)
        if extracted and extracted != "Untitled Document":
            return extracted

        lines = [l.strip() for l in text.split("\n") if l.strip()][:10]
        for line in lines:
            if 10 < len(line) < 150 and not line.startswith("http"):
                return line
        return os.path.splitext(os.path.basename(file_path))[0]

    # ------------------------------------------------------------------
    # PDF Text Extraction
    # ------------------------------------------------------------------

    async def extract_text_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF file."""
        text = ""
        logger.info(f"Extracting text from PDF: {file_path}")

        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            logger.info(f"Extracted {len(text)} chars using pdfplumber")
        except Exception as e:
            logger.warning(f"pdfplumber failed, falling back to PyPDF2: {e}")
            try:
                with open(file_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    for page in pdf_reader.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
                logger.info(f"Extracted {len(text)} chars using PyPDF2")
            except Exception as inner_e:
                logger.error(f"PDF extraction failed: {inner_e}")
                raise Exception(f"Failed to extract text: {str(inner_e)}")

        return self._clean_text(text)

    async def _extract_pages(self, file_path: str) -> List[Dict[str, Any]]:
        """Extract text per page with page numbers."""
        pages = []
        try:
            with pdfplumber.open(file_path) as pdf:
                for i, page in enumerate(pdf.pages):
                    page_text = page.extract_text() or ""
                    pages.append({
                        "page": i + 1,
                        "text": self._clean_text(page_text),
                    })
        except Exception as e:
            logger.warning(f"Per-page extraction failed: {e}")
            # Fallback: whole document as one "page"
            text = await self.extract_text_from_pdf(file_path)
            pages = [{"page": 1, "text": text}]

        return pages

    def _clean_text(self, text: str) -> str:
        """Clean extracted text."""
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n\s*\n+', '\n', text)
        text = re.sub(r'(?m)^\s*\d{1,3}\s*$', '', text)
        return text.strip()

    # ------------------------------------------------------------------
    # Fallback: Traditional Chunking
    # ------------------------------------------------------------------

    def chunk_text(self, text: str) -> List[Dict[str, Any]]:
        """Split text into overlapping chunks (fallback for vector retrieval)."""
        words = text.split()
        chunks = []

        for i in range(0, len(words), self.chunk_size - self.chunk_overlap):
            chunk_words = words[i:i + self.chunk_size]
            chunk_text = ' '.join(chunk_words)

            chunks.append({
                "text": chunk_text,
                "chunk_index": len(chunks),
                "word_count": len(chunk_words)
            })

        return chunks

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    async def extract_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract basic metadata from PDF."""
        metadata = {
            "file_name": os.path.basename(file_path),
            "file_size": os.path.getsize(file_path),
            "extracted_at": datetime.now().isoformat()
        }

        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                info = pdf_reader.metadata

                if info:
                    metadata.update({
                        "title": info.get("/Title", ""),
                        "author": info.get("/Author", ""),
                        "subject": info.get("/Subject", ""),
                    })

                metadata["page_count"] = len(pdf_reader.pages)
        except Exception:
            metadata["page_count"] = 0

        return metadata

    def extract_title_from_text(self, text: str) -> str:
        """Extract likely title from document text."""
        title = self._extract_title_case_sequence(text)
        if title:
            return title

        skip_markers = (
            "provided",
            "permission",
            "copyright",
            "journalistic",
            "scholarly",
            "arxiv",
            "preprint",
            "license",
        )
        lines = [
            line.strip()
            for line in text.split('\n')
            if line.strip() and not any(marker in line.lower() for marker in skip_markers)
        ]

        if lines:
            potential_title = ' '.join(lines[:2])
            if len(potential_title) > 200:
                potential_title = potential_title[:200]
            return potential_title

        return "Untitled Document"

    def _extract_title_case_sequence(self, text: str) -> Optional[str]:
        """Find a clean title-cased paper title in the first page text."""
        window = re.sub(r'\s+', ' ', text[:3000]).strip()
        raw_tokens = re.findall(r"[A-Za-z][A-Za-z\-:]{1,40}", window)

        def is_title_word(token: str) -> bool:
            clean = token.strip(":")
            lower = clean.lower()
            if lower in {
                "provided",
                "providedproperattributionisprovided",
                "permission",
                "journalistic",
                "scholarlyworks",
                "googlebrain",
                "googleresearch",
                "universityoftoronto",
            }:
                return False
            if len(clean) > 24:
                return False
            if re.search(r"[a-z][A-Z]", clean):
                return False
            return bool(re.match(r"^([A-Z][a-z]+|[A-Z]{2,}|of|and|for|to|in|on|with|the|a|an|is|all)$", clean))

        best: List[str] = []
        current: List[str] = []

        for token in raw_tokens:
            clean = token.strip(":")
            if is_title_word(clean):
                current.append(clean)
                continue

            if len(current) >= 3 and len(" ".join(current)) > len(" ".join(best)):
                best = current
            current = []

        if len(current) >= 3 and len(" ".join(current)) > len(" ".join(best)):
            best = current

        if not best:
            return None

        # Avoid returning an author/affiliation list by keeping title-sized runs.
        title = " ".join(best[:16]).strip()
        return title if 10 <= len(title) <= 180 else None

    # ------------------------------------------------------------------
    # Main pipeline (structure + chunk fallback)
    # ------------------------------------------------------------------

    async def process_document(self, file_path: str) -> Dict[str, Any]:
        """Main pipeline: extract, structure, chunk, extract metadata."""
        text = await self.extract_text_from_pdf(file_path)
        metadata = await self.extract_metadata(file_path)
        chunks = self.chunk_text(text)

        if not metadata.get("title"):
            metadata["title"] = self.extract_title_from_text(text)

        return {
            "text": text,
            "chunks": chunks,
            "metadata": metadata,
            "chunk_count": len(chunks),
            "word_count": len(text.split())
        }
