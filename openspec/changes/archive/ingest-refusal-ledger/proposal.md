# Proposal: ingest-refusal-ledger

Issue: #888 — "every ingest refusal must be traceable: the four refusal seams drop
PR: #940
measurements with no ledger, so `make data-gaps` cannot tell 'refused at ingest' from
'never captured'".

## Why

The four ingest refusal seams — fabricated engine (#458), misattribution (#468),
cross-model duplicate copy (#702), weight contradiction (#615) — refuse loudly in the
log and drop the measurement, but leave NO durable trace. `make data-gaps`
(`scripts/data_gap_analysis.py`) can only see a model missing a dimension and reports
it "not stated by any captured post" (an ACQUISITION gap), so the pipeline sends a
re-search after posts it already holds — the exact "we never looked vs we refused"
blindness rule 6o removed for queries, still open for refusals.

## What Changes

- `scripts/update_trending.py` gains the append-only ledger `data/refusals.json` and
  ONE seam `record_ingest_refusals(stage, backend, model, engine, reason, source_post,
  utc)`; `REFUSAL_STAGES` is the single registry of the four seam names — recording an
  unknown stage is REFUSED (rule 6d). Every existing refusal call site records to the
  ledger before dropping the measurement. Rule 3b: entries are only APPENDED; an
  unreadable ledger is never rewritten.
- `scripts/data_gap_analysis.py` reads the ledger (`load_refusals`) and reports a THIRD
  gap class beside acquisition/ingest: **REFUSED at ingest**, naming the stage, model
  and source post; identity-refusal stages are derived from the writer's own registry
  (one implementation, rule 6d). The gap SIGNATURE changes when a refusal changes, so a
  real refusal is a new gap state, not invisible.
- `data/refusals.json` is a new tracked data file (append-only).

## Impact

- `scripts/update_trending.py`, `scripts/data_gap_analysis.py`,
  `tests/test_ingest_refusal_ledger.py` (new suite), `data/refusals.json` (new).
- `make data-gaps` output gains the "REFUSED at ingest" section; no existing report
  section changes.

## Not covered

- Re-accepting refused measurements (the seams keep refusing — the ledger only makes
  the refusal ANALYSABLE).
- Backfilling refusals that happened before this change (the ledger starts empty;
  historical refusals remain log-only).
