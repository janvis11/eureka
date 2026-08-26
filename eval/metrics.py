"""Pure metric functions for eval/run_eval.py.

No I/O, no network, no LLM calls — just scoring logic, so these are cheap
to unit test and safe to reuse from anywhere (see eval tests under
backend/tests/test_eval_metrics.py).
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence


# ---------------------------------------------------------------------------
# Retrieval metrics
# ---------------------------------------------------------------------------

def recall_at_k(retrieved_ids: Sequence[str], relevant_ids: Sequence[str], k: int) -> float:
    """Fraction of relevant ids present in the top-k retrieved ids."""
    if not relevant_ids:
        return 0.0
    top_k = set(retrieved_ids[:k])
    hits = sum(1 for rid in relevant_ids if rid in top_k)
    return hits / len(relevant_ids)


def mrr(retrieved_ids: Sequence[str], relevant_ids: Sequence[str]) -> float:
    """Reciprocal rank of the first relevant id found."""
    relevant_set = set(relevant_ids)
    for i, rid in enumerate(retrieved_ids, start=1):
        if rid in relevant_set:
            return 1.0 / i
    return 0.0


def ndcg_at_k(retrieved_ids: Sequence[str], relevant_ids: Sequence[str], k: int) -> float:
    """Binary-relevance nDCG@k."""
    relevant_set = set(relevant_ids)
    dcg = 0.0
    for i, rid in enumerate(retrieved_ids[:k], start=1):
        if rid in relevant_set:
            dcg += 1.0 / math.log2(i + 1)

    ideal_hits = min(len(relevant_set), k)
    idcg = sum(1.0 / math.log2(i + 1) for i in range(1, ideal_hits + 1))
    return dcg / idcg if idcg > 0 else 0.0


# ---------------------------------------------------------------------------
# Answer grounding
# ---------------------------------------------------------------------------

def verbatim_grounding_rate(answers: List[Dict[str, Any]]) -> Dict[str, Any]:
    """% of cited spans that exist verbatim in their cited chunk.

    Each answer dict: {"citations": [{"quote": str, "chunk_text": str}, ...]}
    A mechanical substring check — no LLM judge involved, so it can't be
    gamed by a model that's good at sounding grounded.
    """
    total = 0
    grounded = 0
    for answer in answers:
        for citation in answer.get("citations", []):
            total += 1
            quote = citation.get("quote", "").strip()
            chunk_text = citation.get("chunk_text", "")
            if quote and quote in chunk_text:
                grounded += 1

    rate = grounded / total if total else 0.0
    return {"grounded": grounded, "total_citations": total, "rate": rate}


# ---------------------------------------------------------------------------
# Abstention
# ---------------------------------------------------------------------------

def abstention_metrics(predictions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Correct-refusal rate on unanswerable questions, false-refusal rate on
    answerable ones.

    Each prediction dict: {"answerable": bool, "abstained": bool}
    """
    answerable = [p for p in predictions if p.get("answerable")]
    unanswerable = [p for p in predictions if not p.get("answerable")]

    correct_refusals = sum(1 for p in unanswerable if p.get("abstained"))
    false_refusals = sum(1 for p in answerable if p.get("abstained"))

    return {
        "unanswerable_total": len(unanswerable),
        "correct_refusals": correct_refusals,
        "correct_refusal_rate": (correct_refusals / len(unanswerable)) if unanswerable else None,
        "answerable_total": len(answerable),
        "false_refusals": false_refusals,
        "false_refusal_rate": (false_refusals / len(answerable)) if answerable else None,
    }


# ---------------------------------------------------------------------------
# Classification metrics (contradiction detection, claim extraction)
# ---------------------------------------------------------------------------

def precision_recall_f1(
    predicted_positive_ids: Sequence[str],
    actual_positive_ids: Sequence[str],
) -> Dict[str, float]:
    """Generic set-based P/R/F1 given predicted vs. gold positive ids."""
    predicted = set(predicted_positive_ids)
    actual = set(actual_positive_ids)

    tp = len(predicted & actual)
    fp = len(predicted - actual)
    fn = len(actual - predicted)

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
    }


def confusion_matrix(
    predictions: List[str],
    labels: List[str],
    classes: Optional[Sequence[str]] = None,
) -> Dict[str, Dict[str, int]]:
    """Multi-class confusion matrix as {actual_class: {predicted_class: count}}.

    Used for the 3-way contradiction verdict (CONTRADICTION /
    CONTEXT_DIFFERENCE / NOT_RELATED) so the biggest false-positive class is
    nameable, not just a single F1 number.
    """
    if classes is None:
        classes = sorted(set(labels) | set(predictions))

    matrix = {actual: {pred: 0 for pred in classes} for actual in classes}
    for pred, label in zip(predictions, labels):
        matrix.setdefault(label, {pred: 0 for pred in classes})
        matrix[label].setdefault(pred, 0)
        matrix[label][pred] += 1

    return matrix
