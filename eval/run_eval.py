#!/usr/bin/env python
"""Eval harness — one command, prints a table, writes eval/results/latest.json.

Usage (from repo root):
    python eval/run_eval.py

Design principle: a capability with
no real gold data is reported as NOT RUN, never silently skipped as if it
scored perfectly. Only contradiction_detection runs against real data today
(eval/gold/contradictions.jsonl has illustrative example pairs) — retrieval,
grounding, and abstention need a live demo corpus plus ~40 real
hand-labeled questions (eval/gold/qa.jsonl) before they can run at all. See
eval/README.md for details.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
REPO_ROOT = EVAL_DIR.parent
BACKEND_DIR = REPO_ROOT / "backend"
GOLD_DIR = EVAL_DIR / "gold"
RESULTS_DIR = EVAL_DIR / "results"

sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(EVAL_DIR))

# app.config.Settings reads its .env relative to CWD — run from backend/ so
# GROQ_API_KEY / OPENAI_API_KEY etc. resolve the same way the app does.
os.chdir(BACKEND_DIR)

from metrics import precision_recall_f1, confusion_matrix  # noqa: E402


def _load_jsonl(path: Path):
    if not path.exists():
        return None
    items = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items or None


def _is_example_only(gold: list) -> bool:
    """Gold files ship with illustrative EXAMPLE rows so the harness has
    something to run before real labels exist. Detect those so results
    computed from them are never reported as if they were real."""
    return all(
        "EXAMPLE" in json.dumps(item).upper() and item.get("note", "").upper().startswith("EXAMPLE")
        for item in gold
    ) and len(gold) <= 5


async def eval_contradictions() -> dict:
    from app.services.discovery.contradiction_verifier import ContradictionVerifier

    gold = _load_jsonl(GOLD_DIR / "contradictions.jsonl")
    if not gold:
        return {"available": False, "reason": "eval/gold/contradictions.jsonl not found or empty"}

    verifier = ContradictionVerifier()
    predictions = []
    labels = []
    for item in gold:
        result = await verifier.verify(item["claim_a_text"], item["claim_b_text"])
        predictions.append(result["verdict"])
        labels.append(item["label"])

    predicted_ids = [i for i, p in enumerate(predictions) if p == "CONTRADICTION"]
    actual_ids = [i for i, l in enumerate(labels) if l == "CONTRADICTION"]
    prf = precision_recall_f1(predicted_ids, actual_ids)
    matrix = confusion_matrix(
        predictions, labels, classes=["CONTRADICTION", "CONTEXT_DIFFERENCE", "NOT_RELATED"]
    )

    return {
        "available": True,
        "is_example_data": _is_example_only(gold),
        "n_pairs": len(gold),
        "precision": round(prf["precision"], 3),
        "recall": round(prf["recall"], 3),
        "f1": round(prf["f1"], 3),
        "confusion_matrix": matrix,
    }


def eval_not_yet_wired(gold_path: Path, needs: str) -> dict:
    gold = _load_jsonl(gold_path)
    if not gold:
        return {"available": False, "reason": f"{gold_path.name} not found or empty"}
    return {
        "available": False,
        "reason": (
            f"{len(gold)} example row(s) found in {gold_path.name}, but this "
            f"metric needs {needs} before it can run for real. Not computed."
        ),
    }


async def main() -> None:
    RESULTS_DIR.mkdir(exist_ok=True)

    results = {
        "contradiction_detection": await eval_contradictions(),
        "retrieval": eval_not_yet_wired(
            GOLD_DIR / "qa.jsonl", "a demo corpus ingested and ~40 real hand-labeled questions"
        ),
        "answer_grounding": eval_not_yet_wired(
            GOLD_DIR / "qa.jsonl", "a demo corpus and real questions"
        ),
        "abstention": eval_not_yet_wired(
            GOLD_DIR / "qa.jsonl", "a demo corpus and 10 real unanswerable questions"
        ),
        "claim_extraction": eval_not_yet_wired(
            GOLD_DIR / "claims.jsonl", "~30 real hand-labeled paragraphs"
        ),
    }

    out_path = RESULTS_DIR / "latest.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\nEval results written to {out_path}\n")
    print(f"{'Capability':<25} {'Status':<10} Detail")
    print("-" * 100)
    for name, r in results.items():
        if r.get("available"):
            flag = " [EXAMPLE DATA, NOT REAL LABELS]" if r.get("is_example_data") else ""
            detail = f"P={r['precision']} R={r['recall']} F1={r['f1']} (n={r['n_pairs']}){flag}"
            print(f"{name:<25} {'OK':<10} {detail}")
        else:
            print(f"{name:<25} {'NOT RUN':<10} {r.get('reason', '')}")
    print()


if __name__ == "__main__":
    asyncio.run(main())
