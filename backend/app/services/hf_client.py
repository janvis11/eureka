"""
Lightweight Hugging Face client for embeddings and local generation.

Features:
- Embeddings using `sentence-transformers` (local encoder)
- Local generation using small instruction models via `transformers` pipelines

This file assumes CPU inference for small models (e.g. `flan-t5-small`).
"""
from typing import List, Optional
import logging

from app.config import get_settings
from app.services.embedding_cache import EmbeddingCache
import hashlib

logger = logging.getLogger(__name__)

# Expose module-level names so unit tests can monkeypatch them easily.
SentenceTransformer = None
pipeline = None
AutoTokenizer = None
AutoModelForSeq2SeqLM = None
try:
    from sentence_transformers import SentenceTransformer as _ST
    SentenceTransformer = _ST
except Exception:
    SentenceTransformer = None

try:
    from transformers import pipeline as _pipeline, AutoTokenizer as _AutoTokenizer, AutoModelForSeq2SeqLM as _AutoModel
    pipeline = _pipeline
    AutoTokenizer = _AutoTokenizer
    AutoModelForSeq2SeqLM = _AutoModel
except Exception:
    pipeline = None
    AutoTokenizer = None
    AutoModelForSeq2SeqLM = None


class HFClient:
    """Client wrapper for local HF models (embeddings + generation).

    - Embeddings use `sentence-transformers` (fast, small models)
    - Generation uses `transformers` pipeline for seq2seq models like `flan-t5-small`
    """

    def __init__(self):
        self.settings = get_settings()
        self._cache = EmbeddingCache(max_items=5000)

        # Lazy imports to keep startup fast when not used
        try:
            # Prefer module-level patched/imported SentenceTransformer
            if SentenceTransformer is not None:
                ST = SentenceTransformer
            else:
                from sentence_transformers import SentenceTransformer as ST

            self._embedding_model = ST(self.settings.EMBEDDING_MODEL)
        except Exception as e:
            logger.error(f"Failed to load SentenceTransformer: {e}")
            self._embedding_model = None

        # Generation pipeline (for discovery / keyword prompts)
        self._generator = None
        if self.settings.HF_USE_LOCAL_GENERATOR:
            try:
                # Prefer module-level pipeline/AutoTokenizer/AutoModel if available
                if pipeline is not None and AutoTokenizer is not None and AutoModelForSeq2SeqLM is not None:
                    _pipeline = pipeline
                    _AutoTokenizer = AutoTokenizer
                    _AutoModel = AutoModelForSeq2SeqLM
                else:
                    from transformers import AutoTokenizer as _AutoTokenizer, AutoModelForSeq2SeqLM as _AutoModel, pipeline as _pipeline

                tokenizer = _AutoTokenizer.from_pretrained(self.settings.DISCOVERY_MODEL, use_fast=True)
                model = _AutoModel.from_pretrained(self.settings.DISCOVERY_MODEL)

                # Create text2text pipeline (CPU device=-1)
                self._generator = _pipeline(
                    "text2text-generation",
                    model=model,
                    tokenizer=tokenizer,
                    device=-1,
                )
            except Exception as e:
                logger.error(f"Failed to initialize local generator pipeline: {e}")
                self._generator = None

    def embed_texts(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """Return embeddings for a list of texts.

        Uses sentence-transformers locally. Returns list of vectors.
        """
        if not self._embedding_model:
            raise RuntimeError("Embedding model not initialized")

        # Use cache to avoid recomputing embeddings for identical texts
        keys = [hashlib.sha256(t.encode('utf-8')).hexdigest() for t in texts]
        cached = self._cache.bulk_get(keys)

        # Determine which texts need embeddings
        to_compute = []
        to_compute_indices = []
        for i, c in enumerate(cached):
            if c is None:
                to_compute.append(texts[i])
                to_compute_indices.append(i)

        results = [None] * len(texts)
        # Fill from cache
        for i, c in enumerate(cached):
            if c is not None:
                results[i] = c

        if to_compute:
            embeddings = self._embedding_model.encode(to_compute, batch_size=batch_size, show_progress_bar=False, convert_to_numpy=True)
            # embeddings is numpy array; convert each and store
            for idx, emb in enumerate(embeddings):
                emb_list = emb.tolist()
                orig_index = to_compute_indices[idx]
                results[orig_index] = emb_list
                self._cache.set(keys[orig_index], emb_list)

        # Final results
        return results

    def embed_text(self, text: str) -> List[float]:
        key = hashlib.sha256(text.encode('utf-8')).hexdigest()
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        emb = self.embed_texts([text])[0]
        # cache already set in embed_texts
        return emb

    def generate(self, prompt: str, max_length: int = 256, temperature: float = 0.0) -> str:
        """Generate text using local HF generator (if available).

        Falls back to a RuntimeError if generator is not initialized.
        """
        if not self._generator:
            raise RuntimeError("Local HF generator not initialized")

        try:
            outputs = self._generator(prompt, max_length=max_length, do_sample=False)
            if outputs and isinstance(outputs, list):
                text = outputs[0].get("generated_text") or outputs[0].get("summary_text") or outputs[0].get("text") or ""
                return text
            return ""
        except Exception as e:
            logger.error(f"HF generation error: {e}")
            raise
