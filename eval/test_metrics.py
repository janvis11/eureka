"""Unit tests for eval/metrics.py — run with `pytest eval/` from repo root."""

from metrics import (
    abstention_metrics,
    confusion_matrix,
    mrr,
    ndcg_at_k,
    precision_recall_f1,
    recall_at_k,
    verbatim_grounding_rate,
)


def test_recall_at_k():
    retrieved = ["a", "b", "c", "d"]
    relevant = ["b", "d", "z"]
    assert recall_at_k(retrieved, relevant, k=4) == 2 / 3
    assert recall_at_k(retrieved, relevant, k=1) == 0.0


def test_mrr_first_hit_position():
    assert mrr(["a", "b", "c"], ["b"]) == 0.5
    assert mrr(["a", "b", "c"], ["a"]) == 1.0
    assert mrr(["a", "b", "c"], ["z"]) == 0.0


def test_ndcg_perfect_ranking_is_one():
    assert ndcg_at_k(["a", "b"], ["a", "b"], k=2) == 1.0


def test_ndcg_no_relevant_found_is_zero():
    assert ndcg_at_k(["a", "b"], ["z"], k=2) == 0.0


def test_verbatim_grounding_rate():
    answers = [
        {"citations": [
            {"quote": "attention is all you need", "chunk_text": "the paper attention is all you need shows..."},
            {"quote": "made up quote", "chunk_text": "unrelated text"},
        ]},
    ]
    result = verbatim_grounding_rate(answers)
    assert result == {"grounded": 1, "total_citations": 2, "rate": 0.5}


def test_verbatim_grounding_rate_no_citations():
    assert verbatim_grounding_rate([{"citations": []}])["rate"] == 0.0


def test_abstention_metrics():
    predictions = [
        {"answerable": True, "abstained": False},
        {"answerable": True, "abstained": True},   # false refusal
        {"answerable": False, "abstained": True},  # correct refusal
        {"answerable": False, "abstained": False}, # missed refusal
    ]
    result = abstention_metrics(predictions)
    assert result["correct_refusal_rate"] == 0.5
    assert result["false_refusal_rate"] == 0.5


def test_precision_recall_f1():
    predicted = ["p1", "p2", "p3"]
    actual = ["p1", "p4"]
    result = precision_recall_f1(predicted, actual)
    assert result["true_positives"] == 1
    assert result["false_positives"] == 2
    assert result["false_negatives"] == 1
    assert round(result["precision"], 3) == round(1 / 3, 3)
    assert result["recall"] == 0.5


def test_confusion_matrix():
    predictions = ["CONTRADICTION", "CONTEXT_DIFFERENCE", "CONTRADICTION"]
    labels = ["CONTRADICTION", "CONTRADICTION", "NOT_RELATED"]
    matrix = confusion_matrix(predictions, labels)
    assert matrix["CONTRADICTION"]["CONTRADICTION"] == 1
    assert matrix["CONTRADICTION"]["CONTEXT_DIFFERENCE"] == 1
    assert matrix["NOT_RELATED"]["CONTRADICTION"] == 1
