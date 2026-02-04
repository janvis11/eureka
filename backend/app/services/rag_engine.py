"""
Simple RAG Engine: semantic search + LLM answer generation.
Uses FAISS for embeddings, Groq for LLM.
"""

from typing import List, Dict, Any
from groq import Groq
import faiss
import numpy as np
import os
from app.config import get_settings
from typing import Optional
from app.services.shared import hf_client as shared_hf_client
import logging

logger = logging.getLogger(__name__)
settings = get_settings()


class RAGEngine:
    """Retrieval-Augmented Generation using FAISS + Groq."""
    
    def __init__(self, hf_client: Optional[object] = None):
        self.settings = settings
        
        # Initialize FAISS index
        self.embedding_dim = 384  # all-MiniLM-L6-v2 embedding dimension
        self.index = faiss.IndexFlatL2(self.embedding_dim)
        
        # Store document texts and metadata
        self.documents = []
        self.metadatas = []
        self.doc_ids = []
        
        # FAISS index file path
        self.index_path = os.path.join(settings.CHROMADB_PATH, "faiss_index.bin")
        self.metadata_path = os.path.join(settings.CHROMADB_PATH, "metadata.pkl")
        
        # Create data directory if needed
        os.makedirs(settings.CHROMADB_PATH, exist_ok=True)
        
        # Load existing index if available
        self._load_index()
        
        # Use provided HF client or shared singleton
        self.hf_client = hf_client or shared_hf_client
        
        # Initialize Groq LLM (optional)
        try:
            self.groq_client = Groq(api_key=settings.GROQ_API_KEY)
        except Exception:
            self.groq_client = None
        
        logger.info("RAG Engine initialized with FAISS")
    
    def _load_index(self):
        """Load persisted FAISS index and metadata."""
        try:
            if os.path.exists(self.index_path):
                self.index = faiss.read_index(self.index_path)
                logger.info(f"Loaded FAISS index with {self.index.ntotal} vectors")
                
                # Load metadata
                if os.path.exists(self.metadata_path):
                    import pickle
                    with open(self.metadata_path, 'rb') as f:
                        data = pickle.load(f)
                        self.documents = data.get('documents', [])
                        self.metadatas = data.get('metadatas', [])
                        self.doc_ids = data.get('doc_ids', [])
                    logger.info(f"Loaded {len(self.documents)} documents")
        except Exception as e:
            logger.warning(f"Could not load index: {e}, starting fresh")
    
    def _save_index(self):
        """Persist FAISS index and metadata to disk."""
        try:
            os.makedirs(settings.CHROMADB_PATH, exist_ok=True)
            faiss.write_index(self.index, self.index_path)
            
            # Save metadata
            import pickle
            with open(self.metadata_path, 'wb') as f:
                pickle.dump({
                    'documents': self.documents,
                    'metadatas': self.metadatas,
                    'doc_ids': self.doc_ids
                }, f)
            logger.info("Index saved to disk")
        except Exception as e:
            logger.error(f"Error saving index: {e}")
    
    async def add_document_chunks(
        self,
        chunks: List[Dict[str, Any]],
        document_id: int,
        metadata: Dict[str, Any]
    ) -> int:
        """Add document chunks to vector store."""
        try:
            texts = []
            metadatas = []
            ids = []

            for i, chunk in enumerate(chunks):
                text = chunk.get("text", "")
                if not text:
                    continue

                # Prepare metadata
                chunk_metadata = {
                    "document_id": str(document_id),
                    "chunk_index": chunk.get("chunk_index", i),
                    "document_title": metadata.get("title", "Unknown"),
                    "page_count": metadata.get("page_count", 0)
                }

                texts.append(text)
                metadatas.append(chunk_metadata)
                ids.append(f"doc_{document_id}_chunk_{i}")

            # Create embeddings in batch via HFClient
            if texts:
                embeddings = self.hf_client.embed_texts(texts)
                
                # Convert to numpy array and reshape if needed
                embeddings_array = np.array(embeddings, dtype=np.float32)
                
                # Add to FAISS index
                self.index.add(embeddings_array)
                
                # Store documents and metadata
                self.documents.extend(texts)
                self.metadatas.extend(metadatas)
                self.doc_ids.extend(ids)
                
                # Save to disk
                self._save_index()

                logger.info(f"Added {len(texts)} chunks from document {document_id}")
                return len(texts)
            
            return 0
        
        except Exception as e:
            logger.error(f"Error adding document chunks: {e}")
            raise
    
    async def semantic_search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search for relevant document chunks."""
        try:
            if self.index.ntotal == 0:
                logger.warning("No documents in index")
                return []
            
            # Create query embedding via HFClient
            query_embedding = self.hf_client.embed_text(query)
            query_array = np.array([query_embedding], dtype=np.float32)
            
            # Search in FAISS
            distances, indices = self.index.search(query_array, min(top_k, self.index.ntotal))
            
            # Format results
            formatted_results = []
            for i, idx in enumerate(indices[0]):
                if idx >= 0 and idx < len(self.documents):
                    formatted_results.append({
                        "text": self.documents[idx],
                        "metadata": self.metadatas[idx],
                        "distance": float(distances[0][i])
                    })
            
            return formatted_results
        
        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            return []
    
    async def generate_answer(
        self,
        question: str,
        context: List[Dict[str, Any]],
        max_tokens: int = None
    ) -> Dict[str, Any]:
        """Generate answer using LLM with retrieved context."""
        try:
            if not context:
                return {
                    "answer": "No relevant information found.",
                    "confidence": 0.0
                }
            
            # Build context string
            context_text = "\n\n".join([
                f"Source {i+1} (Distance: {c.get('distance', 0):.4f}):\n{c.get('text', '')}"
                for i, c in enumerate(context[:3])
            ])
            
            # Create prompt
            prompt = f"""You are a research assistant. Answer the following question based on the provided context.

QUESTION: {question}

CONTEXT:
{context_text}

INSTRUCTIONS:
1. Answer the question directly and concisely
2. Only use information from the context
3. If the answer is not in the context, say "I don't have enough information"
4. Be accurate and avoid speculation

ANSWER:"""
            
            # Call Groq LLM
            response = self.groq_client.chat.completions.create(
                model=self.settings.LLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.settings.LLM_TEMPERATURE,
                max_tokens=self.settings.LLM_MAX_TOKENS
            )
            
            answer = response.choices[0].message.content
            
            # Calculate confidence based on context relevance (lower distance = higher confidence)
            avg_distance = sum(c.get('distance', 0) for c in context) / len(context)
            confidence = max(0, 1 - avg_distance / 100)  # Normalize FAISS L2 distance
            
            return {
                "answer": answer,
                "confidence": round(confidence, 2)
            }
        
        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            return {
                "answer": f"Error generating answer: {str(e)}",
                "confidence": 0.0
            }
    
    async def delete_document(self, document_id: int) -> bool:
        """Delete document from vector store."""
        try:
            # Find all chunks for this document
            indices_to_remove = []
            for i, metadata in enumerate(self.metadatas):
                if metadata.get("document_id") == str(document_id):
                    indices_to_remove.append(i)
            
            if not indices_to_remove:
                logger.warning(f"No chunks found for document {document_id}")
                return False
            
            # FAISS doesn't support direct deletion, so we rebuild the index
            # Remove in reverse order to maintain indices
            for idx in sorted(indices_to_remove, reverse=True):
                del self.documents[idx]
                del self.metadatas[idx]
                del self.doc_ids[idx]
            
            # Rebuild index
            self._rebuild_index()
            self._save_index()
            
            logger.info(f"Deleted document {document_id} from vector store")
            return True
        
        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            return False
    
    def _rebuild_index(self):
        """Rebuild FAISS index from stored documents."""
        try:
            # Create new index
            self.index = faiss.IndexFlatL2(self.embedding_dim)
            
            # Re-embed all documents
            if self.documents:
                embeddings = self.hf_client.embed_texts(self.documents)
                embeddings_array = np.array(embeddings, dtype=np.float32)
                self.index.add(embeddings_array)
                logger.info(f"Rebuilt index with {self.index.ntotal} vectors")
        except Exception as e:
            logger.error(f"Error rebuilding index: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics."""
        return {
            "total_chunks": self.index.ntotal,
            "total_documents": len(set([m.get("document_id") for m in self.metadatas])),
            "embedding_dim": self.embedding_dim,
            "index_type": "FAISS"
        }