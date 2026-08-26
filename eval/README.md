# Eval harness

One command, from the repo root:

```bash
python eval/run_eval.py
```

Writes `eval/results/latest.json` and prints a table. Every metric reports
`NOT RUN` with a specific reason instead of a fake number when the gold
data it needs isn't there yet.

## What's real right now

- **`contradiction_detection`** actually runs: `eval/gold/contradictions.jsonl`
  has 5 illustrative example pairs and the harness calls the live
  two-stage verifier (`ContradictionMiner` candidate → LLM verify) against
  them and reports precision/recall/F1 + confusion matrix.
- **`retrieval`, `answer_grounding`, `abstention`, `claim_extraction`** are
  wired up (see `metrics.py`) but need a live demo corpus and real
  hand-labeled questions/paragraphs before they can run.

## The 5 example contradiction pairs are not your gold set

They exist so the harness has something to execute today and so you can
see the output shape. A real gold set needs on the order of **60–80
hand-labeled pairs** — every row in `eval/gold/contradictions.jsonl` is
flagged with `"note": "EXAMPLE — ..."` and the run output is tagged
`[EXAMPLE DATA, NOT REAL LABELS]` for exactly this reason. Replace the file
with your own labeled pairs before reporting these numbers anywhere.

**Do not use an LLM to generate the labels.** If a reviewer asks "who
labelled this?" and the answer is "GPT," the whole metrics section is
invalidated on contact.

## Gold file formats

- `gold/contradictions.jsonl` — one claim pair per line:
  `{"claim_a_text": "...", "claim_b_text": "...", "label": "CONTRADICTION|CONTEXT_DIFFERENCE|NOT_RELATED"}`
- `gold/qa.jsonl` — one question per line:
  `{"question": "...", "answerable": true|false, "answer_paper": "...", "answer_section": "..."}`
  (include ~10 `answerable: false` rows — that's how abstention correctness
  gets measured)
- `gold/claims.jsonl` — one paragraph per line:
  `{"paragraph": "...", "gold_claims": ["...", "..."]}`

## Adding the retrieval/grounding/abstention evals for real

Once a demo corpus exists and `qa.jsonl` has real labeled
questions, extend `run_eval.py`'s `eval_not_yet_wired` calls to actually:
1. Run `HybridRetriever`/`RAGEngine` retrieval for each question, compare
   retrieved chunk ids against `answer_paper`/`answer_section` using
   `metrics.recall_at_k` / `mrr` / `ndcg_at_k`.
2. Run the full answer path, check citations against chunk text with
   `metrics.verbatim_grounding_rate`.
3. Check `abstained` on the `answerable: false` rows with
   `metrics.abstention_metrics`.

`metrics.py` has no I/O and is unit-tested in `eval/test_metrics.py` — run
`pytest eval/` to check it.
