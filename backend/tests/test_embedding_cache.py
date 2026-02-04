from app.services.embedding_cache import EmbeddingCache


def test_cache_set_get():
    cache = EmbeddingCache(max_items=3)
    cache.set('a', [1,2,3])
    cache.set('b', [4,5,6])
    assert cache.get('a') == [1,2,3]
    assert cache.get('b') == [4,5,6]


def test_cache_eviction():
    cache = EmbeddingCache(max_items=2)
    cache.set('a', [1])
    cache.set('b', [2])
    cache.set('c', [3])
    assert cache.get('a') is None  # evicted
    assert cache.get('b') == [2]
    assert cache.get('c') == [3]
