# Proposal: measurement-attribution-refusal

Issue: tech-debt — "A measurement names a different model than the row it is stored on"
(measured while implementing #456; surfaced by PR #468).

## Why

`data/models.json` → `qwen-3.6-27b`, measurement `llama.cpp` 140 t/s on `RTX 5090 32GB`:
its `quant` reads "Qwen 3.5 35B served through LM Studio anthropic-compatible endpoint
(v1/messages), 80k context, model fully in VRAM" — the run is Qwen 3.5 35B, not Qwen 3.6
27B. A misplaced measurement inflates the row's `tps` and its `posts_7d` signal, and
AGENTS.md §3 requires every figure to trace to a `…/status/<id>` post; it also keeps an
`unstructured:context_tokens` claim alive whose only post names another model.

The same row's OTHER measurement carries `"source_post": "https://lightbrd.com/"`, a
placeholder rather than a post — and `check_post_signal` accepted it as a low-signal row
without noticing that a placeholder carrying engagement counts is fabricated attribution.

## What Changes

- **`scripts/update_trending.py`** gains `measurement_model_identity`,
  `named_models_in_text`, `misattributed_measurement_reason`,
  `refuse_misattributed_measurements` and `fabricated_post_signal_reason`:
  - A measurement whose `quant`/`why` text names a model of the SAME family with a
    DIFFERENT parameter size than the row it would merge into is REFUSED at ingest, loudly,
    carrying the source post so a human can open the evidence.
  - Cross-family mentions are comparison context; a comparison cue (`vs`, `versus`,
    `compared`, `baseline`, `than`, `beats`, `against`, `not the`, `instead of`, `while`)
    rescues a bake-off sentence; a text that names the row's own model is a multi-model
    post about this row; and `MEASUREMENT_MODEL_ALIASES` documents the remaining real
    exceptions (the issue's "or needs an explicit alias mapping").
  - A row whose own identity cannot be parsed fails open (never guesses a refusal).
- **`scripts/validate.py`**:
  - `check_post_signal` now FAILS a measurement whose `source_post` is a placeholder AND
    which claims positive engagement counts — the count cannot come from a post nobody
    can open. A placeholder with NO counts stays a warning (the low-signal, static
    historical row the issue's carve-out protects).
  - A new report-only scan, `check_measurement_attribution`, prints the historical rows
    whose text names another model (the shipped store has one: `qwen-3.6-27b`) without
    reding every PR for history it cannot repair — the same pattern as
    `check_duplicate_runs` (#459).
- **Tests:** `tests/test_measurement_attribution.py` (new) locks the refusal, the carve-
  outs and the report-only scan; `tests/test_post_signal.py` gains the placeholder+counts
  failure and keeps the coverage warning.

## Impact

`scripts/update_trending.py`, `scripts/validate.py`, `tests/test_measurement_attribution.py`,
`tests/test_post_signal.py`, this OpenSpec change and the regenerated `OPENSPEC.md`. No new
target, stage, workflow or image (`ARCHITECTURE.md` unchanged, rule 6h); the new scan is
registered under the existing `data` stage and reaches CI through `make validate` (rule 6d).

## Not covered

- **The shipped `qwen-3.6-27b` row is NOT removed by this change.** Ingest refuses NEW
  misattributed measurements; the historical row stays until a refresh replaces its
  measurement or a human edits the store. Reding every PR for history it cannot repair is
  what #458/#459 refused to do, so the scan reports it and the next refresh's ingest
  refusal prevents a recurrence.
- **A comparison post that measures two models in one figure** (one t/s for both) is not
  detected; the comparison cue deliberately keeps it. Splitting a joint figure needs the
  post's own wording, which is a separate change.
- **The `MEASUREMENT_MODEL_ALIASES` map ships empty.** Every current row parses under the
  strict rule, so no entry is needed yet; an entry is added only when a real variant or
  bake-off row needs it, with a comment saying why.
