"""Shared retry policy for model gateway network calls.

Every provider hits the same class of transient failure (rate limits,
connection resets, brief provider outages) at the same place: the actual
SDK call. A single small decorator here avoids each provider reimplementing
retry/backoff, while keeping the per-provider fallback logic (e.g.
GroqProvider falling back to a local embedder) unchanged — retries happen
first, and the provider's own except block still runs if all attempts fail.
"""

from __future__ import annotations

import logging

from tenacity import retry, stop_after_attempt, wait_exponential, before_sleep_log

logger = logging.getLogger(__name__)

retry_llm_call = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    reraise=True,
    before_sleep=before_sleep_log(logger, logging.WARNING),
)
