import os
import PyPDF2
import pdfplumber
from typing import List, Dict, Any
import re
from datetime import datetime


class DocumentProcessor:
    """Simple document processor: extract text, chunk, minimal processing."""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    async def extract_text_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF file."""
        text = ""
        
        try:
            # Try pdfplumber first (better for complex layouts)
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e:
            # Fallback to PyPDF2
            try:
                with open(file_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    for page in pdf_reader.pages:
                        text += page.extract_text() + "\n"
            except Exception as inner_e:
                raise Exception(f"Failed to extract text: {str(inner_e)}")
        
        return self._clean_text(text)
    
    def _clean_text(self, text: str) -> str:
        """Clean extracted text - simple approach."""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove page numbers (common patterns)
        text = re.sub(r'\b\d{1,3}\s*$', '', text, flags=re.MULTILINE)
        return text.strip()
    
    def chunk_text(self, text: str) -> List[Dict[str, Any]]:
        """Split text into overlapping chunks for embedding."""
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
        except Exception as e:
            metadata["page_count"] = 0
        
        return metadata
    
    def extract_title_from_text(self, text: str) -> str:
        """Extract likely title from document text."""
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        if lines:
            # First few lines often contain title
            potential_title = ' '.join(lines[:3])
            if len(potential_title) > 200:
                potential_title = potential_title[:200]
            return potential_title
        
        return "Untitled Document"
    
    async def process_document(self, file_path: str) -> Dict[str, Any]:
        """Main pipeline: extract, chunk, extract metadata."""
        # Extract text
        text = await self.extract_text_from_pdf(file_path)
        
        # Extract metadata
        metadata = await self.extract_metadata(file_path)
        
        # Chunk text
        chunks = self.chunk_text(text)
        
        # Extract title if not in metadata
        if not metadata.get("title"):
            metadata["title"] = self.extract_title_from_text(text)
        
        return {
            "text": text,
            "chunks": chunks,
            "metadata": metadata,
            "chunk_count": len(chunks),
            "word_count": len(text.split())
        }
