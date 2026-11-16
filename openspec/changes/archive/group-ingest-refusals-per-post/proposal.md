# Proposal: group-ingest-refusals-per-post

Issue: #882 — "Re-captured posts repeat refusal noise across search legs; group the
PR: #1102
refusal report per (post, rule)"

## Why

A post captured by several legs lands in several `data/raw/*.json` snapshots, and
every re-merge re-walks it through the four ingest refusal seams
(`refuse_fabricated_engines`, `refuse_misattributed_measurements`,
`refuse_cross_model_duplicate_measurements`, `refuse_weight_gb_contradictions`).
Measured replay of all shipped raw snapshots against a copy of the shipped store:
**253 measurement refusals printed 253 individual `[ingest] REFUSED` lines** —
e.g. one MLX 18 t/s copy was refused 11 times, its line repeated once per snapshot
(`amd-…-114107-7.json` then `cpu-…114107-7.json` then `nvidia-…`). The repetition
grows with legs × snapshots and buries NEW refusals in the noise — the exact
quality loss issue #882 names.

## What Changes

- `scripts/update_trending.py`: each seam's refusal is recorded through
  `_note_run_refusal`, keyed `(rule, model id, engine, source post)`; the four
  per-snapshot prints are replaced by ONE grouped flush at the end of
  `ingest_raw_snapshots`, naming every snapshot a repeated refusal was seen in
  (`— seen 11x across snapshots: …, …, … (+8 more)`).
- The refusals themselves, their `data/refusals.json` records, the per-file ledger
  summaries and the run-level refusal-count line are **unchanged** — only the log
  line dedupes (rule 3b: no count shrinks; `make data-gaps` reads the same ledger).
- `tests/test_ingest_refusal_grouping.py` (new): the thrice-captured post prints
  exactly one grouped line; distinct refusals each keep their own line (dedup never
  swallows); the shipped-raw replay prints each `(rule, engine, model, post)`
  refusal at most once while the refusal COUNT stays the full number.
- `tests/test_cross_model_attribution.py`: the wiring assertion now proves the seam
  feeds the grouped flush (rule 6b — test updates ride the format change).

## Impact

- Bot logs drop from 253 repeated refusal lines to 106 grouped ones on the shipped
  replay; a NEW refusal is no longer hidden inside repeats of an old one.
- No ingest decision, ledger record, validator or README behaviour changes.

## Not covered

- The per-file `[ingest] <file>: N refusal(s) recorded…` summaries (they name the
  file each ledger batch came from — a per-run group would lose that).
- The post URLs themselves: capture-side dedup across legs is a separate question.
