# Proposal: refusals-ledger-seen-count-idempotent

Issue: #1148

## Why

`record_ingest_refusals` (rule #888) appends one record per refusal per validation
pass, and no pass ever repeats a finding. Measured on `data/refusals.json`
2026-11-19: 92 records hold only **3 distinct** (model, engine, reason) findings —
`deepseek-v4-pro` 4×, `kimi-k2.7-code` 24×, `qwen-3.5-122b-a10b` 64× — so the
finding a reader must act on is buried under copies of it, and `make data-gaps`
reports a total that is a count of runs rather than a count of gaps (issue #1148).

## What Changes

- `record_ingest_refusals` keys a finding on
  `(stage, model, engine, reason, source_post)`. A finding not yet recorded appends
  exactly one record with `seen_count: 1`. A finding already recorded raises its
  `seen_count` and stamps `last_seen_utc` on that record — no copy is appended, and
  the record's original `utc` (its first sighting) never moves (rule 3b: a key may
  only be ADDED, a counter may only GROW, no recorded value is shrunk or removed).
- The collapse is announced once per call: `[ingest] refusals ledger: N new record(s),
  M repeat(s) counted on the record already there`.
- `data_gap_analysis` carries `seen_count` into `refused_at_ingest` and prints the
  refusal total as the SUM of `seen_count` (observations), so collapsing repeats
  into counters can never shrink a number an earlier report printed (rule 3b).
- `tests/test_ingest_refusal_ledger.py` gains four guards driven through the real
  writer and the real analysis.

## Impact

- `scripts/update_trending.py` — `record_ingest_refusals` (writer) and its docstring.
- `scripts/data_gap_analysis.py` — `refused_at_ingest` keys, refusal total.
- `tests/test_ingest_refusal_ledger.py` — 4 new tests (13 tests in the module).
- `data/refusals.json` — the existing 92 records are NOT rewritten (rule 3b: no
  removal); the next validation pass grows counters on the records already there
  instead of appending copies, and no existing key or value changes.
- Not covered: collapsing the historical duplicates (a human decision, rule 3b);
  any change to which seams record a refusal.
