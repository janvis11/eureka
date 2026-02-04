"""Simple in-memory LRU cache for embeddings."""
from collections import OrderedDict
from typing import List, Optional


class EmbeddingCache:
    def __init__(self, max_items: int = 10000):
        self.max_items = max_items
        self.store = OrderedDict()

    def get(self, key: str) -> Optional[List[float]]:
        if key in self.store:
            # Move to end (most recently used)
            self.store.move_to_end(key)
            return self.store[key]
        return None

    def set(self, key: str, value: List[float]):
        self.store[key] = value
        self.store.move_to_end(key)
        if len(self.store) > self.max_items:
            self.store.popitem(last=False)

    def bulk_get(self, keys: List[str]) -> List[Optional[List[float]]]:
        return [self.get(k) for k in keys]

    def clear(self):
        self.store.clear()
