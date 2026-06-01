"""Small local embedding fallback used when API embeddings are unavailable.

This is not a replacement for production semantic embeddings, but it gives the
app dependable lexical retrieval during development, demos, and provider quota
outages. It is deterministic, dependency-free, and uses the same vector shape
for documents and queries.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections import Counter
from typing import Iterable, List


DEFAULT_LOCAL_EMBEDDING_DIM = 384

_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_+\-/\.]{1,}", re.IGNORECASE)
_STOP_WORDS = {
    "about",
    "after",
    "also",
    "and",
    "are",
    "because",
    "been",
    "being",
    "between",
    "but",
    "can",
    "does",
    "for",
    "from",
    "has",
    "have",
    "how",
    "into",
    "its",
    "may",
    "more",
    "not",
    "of",
    "on",
    "only",
    "or",
    "our",
    "paper",
    "papers",
    "research",
    "show",
    "shows",
    "such",
    "than",
    "that",
    "the",
    "their",
    "there",
    "these",
    "this",
    "through",
    "use",
    "used",
    "using",
    "was",
    "were",
    "what",
    "when",
    "where",
    "which",
    "with",
    "without",
}


def embed_texts(
    texts: Iterable[str],
    dimension: int = DEFAULT_LOCAL_EMBEDDING_DIM,
) -> List[List[float]]:
    """Embed texts with signed feature hashing and L2 normalization."""
    return [_embed_one(text or "", dimension=dimension) for text in texts]


def _embed_one(text: str, dimension: int) -> List[float]:
    vector = [0.0] * dimension
    features = Counter(_features(text))

    if not features:
        return vector

    for feature, count in features.items():
        digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
        bucket = int.from_bytes(digest[:4], "big") % dimension
        sign = 1.0 if digest[4] & 1 else -1.0
        vector[bucket] += sign * (1.0 + math.log(count))

    norm = math.sqrt(sum(v * v for v in vector))
    if norm:
        vector = [v / norm for v in vector]

    return vector


def _features(text: str) -> Iterable[str]:
    tokens = [
        token.lower().strip("._-/")
        for token in _TOKEN_RE.findall(text)
    ]
    tokens = [
        token
        for token in tokens
        if len(token) > 1 and token not in _STOP_WORDS
    ]

    for token in tokens:
        yield f"tok:{token}"

        # Character shingles help with extracted-PDF glitches and variants.
        if len(token) >= 5:
            padded = f"_{token}_"
            for i in range(len(padded) - 3):
                yield f"chr:{padded[i:i + 4]}"

    for left, right in zip(tokens, tokens[1:]):
        yield f"bi:{left} {right}"

    for a, b, c in zip(tokens, tokens[1:], tokens[2:]):
        yield f"tri:{a} {b} {c}"
