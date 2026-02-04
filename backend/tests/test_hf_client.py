import pytest
import types
import numpy as np

from app.services.hf_client import HFClient


class DummyST:
    def __init__(self, *args, **kwargs):
        pass

    def encode(self, texts, batch_size=32, show_progress_bar=False, convert_to_numpy=True):
        # Return deterministic embeddings for tests
        arr = np.array([[float(len(t))] * 8 for t in texts])
        return arr


class DummyGen:
    def __init__(self, *args, **kwargs):
        pass

    def __call__(self, prompt, max_length=128, do_sample=False):
        return [{"generated_text": "DUMMY_GENERATION: " + prompt[:50]}]


@pytest.fixture(autouse=True)
def patch_sentence_transformers(monkeypatch):
    # Patch SentenceTransformer and transformers pipeline imports used in HFClient
    import app.services.hf_client as hf_mod

    monkeypatch.setattr(hf_mod, "SentenceTransformer", DummyST)

    # Patch pipeline used for generation
    class DummyPipeline:
        def __call__(self, prompt, max_length=128, do_sample=False):
            return [{"generated_text": "DUMMY_GENERATION: " + prompt[:50]}]

    monkeypatch.setattr(hf_mod, "pipeline", lambda *args, **kwargs: DummyPipeline())
    yield


def test_embed_texts_and_cache():
    client = HFClient()
    texts = ["hello world", "another text"]
    embeddings = client.embed_texts(texts)
    assert isinstance(embeddings, list)
    assert len(embeddings) == 2
    assert len(embeddings[0]) == 8

    # second call should hit cache (no error)
    embeddings2 = client.embed_texts(texts)
    assert embeddings2 == embeddings


def test_generate():
    client = HFClient()
    # monkeypatched generator returns predictable output
    if client._generator is None:
        pytest.skip("Generator not initialized in test environment")

    out = client.generate("Summarize this text:")
    assert isinstance(out, str)
    assert out.startswith("DUMMY_GENERATION")
