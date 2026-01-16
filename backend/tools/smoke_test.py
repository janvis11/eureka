"""
Quick smoke test for local HF client: embeddings + generation.

This script runs a minimal embedding + generation flow using the shared HF client.
It is intended for local dev to verify the local HF pipeline is wired correctly.

Usage:
    python tools/smoke_test.py

Note: This will attempt to load local models (sentence-transformers + flan-t5-small).
If you don't want to download models, run the unit tests which mock these components.
"""
import asyncio
import logging

from app.services.shared import hf_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("smoke_test")

SAMPLE_TEXTS = [
    "This is a short scientific abstract about machine learning and graph neural networks.",
    "We propose a new method that improves classification accuracy by 3% on benchmark datasets."
]

PROMPT = "Generate a one-sentence summary of the following: {}"


async def run_smoke():
    logger.info("Running smoke test: embeddings")
    try:
        embeds = hf_client.embed_texts(SAMPLE_TEXTS)
        logger.info(f"Embeddings generated for {len(embeds)} texts; dim={len(embeds[0]) if embeds else 'N/A'}")
    except Exception as e:
        logger.error(f"Embedding failed: {e}")
        return

    logger.info("Running smoke test: generation")
    try:
        prompt = PROMPT.format(SAMPLE_TEXTS[0])
        out = hf_client.generate(prompt, max_length=64)
        logger.info(f"Generation output: {out}")
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        return

    logger.info("Smoke test completed successfully")


if __name__ == '__main__':
    asyncio.run(run_smoke())
