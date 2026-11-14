# Proposal: measurement-identity-tps-912

Issue: #912
PR: #931

## Why

The #411 captured-text join keys a measurement by the exact
`(engine, tps, hardware, source_post)` tuple. AGENTS.md rule 3b lets a
measurement's t/s be RAISED at ingest (`merge_engines` does exactly that when a
newer post reports a higher figure for the same run). After such a raise the
store tuple no longer equals the raw tuple, the join silently stops matching,
and the row's footprint text degrades from ingest-class back to untraceable —
the same "we never looked" blindness #264/#414 removed, reintroduced through
the `tps` field.

## What Changes

- `scripts/data_gap_analysis.py::_join_measurement_identity` also joins by
  POST identity `(engine, hardware, source_post)`: when a raw tuple matches a
  unique store carrier on that key and the stored tps is numerically **≥** the
  captured tps (a legitimate raise), the text is credited — the measurement is
  provably the same run. A measurement with NO source post still requires an
  equal tps (without a post, tps itself is the only link). A joint (two
  carriers) or unowned identity keeps crediting NOTHING (the #411 rule).
- Missed identities — a raw tuple whose post identity matches a store row but
  whose tps comparison FAILS — are reported loudly by `captured_text`
  (a `measurement-identity:` line naming the misses), never silently dropped.
- New tests in `tests/test_data_gap_analysis.py` pin all four shapes.

## Impact

- `scripts/data_gap_analysis.py` (join + loud report), `tests/test_data_gap_analysis.py`
- AGENTS.md §8 guard row

## Not covered

- `update_trending._cross_model_identity` is UNTOUCHED — it is the #702 ingest
  refusal key and `validate.same_post_cross_model_duplicates` read it; this
  change widens only the ANALYSIS-side join (analysis never mutates the store).
