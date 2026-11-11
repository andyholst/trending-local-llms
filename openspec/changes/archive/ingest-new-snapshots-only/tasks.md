# Tasks

- [x] 1. Write the proposal + capability spec for issue #175 (`ingest-boundary`: a merge folds in only the snapshots newer than the store, the derived/overridable boundary, the corrected-snapshot re-merge, the wiring).
- [x] 2. `scripts/update_trending.py` — `parse_utc_stamp` + `raw_snapshot_stamp` (the one definition of "when was this snapshot captured": its `generated_utc`, else the filename stamp, else undateable).
- [x] 3. `scripts/update_trending.py` — `ingest_raw_snapshots(store, since=None)` skips a snapshot that is not strictly newer than `since`, and merges an undateable one (fail-open).
- [x] 4. `scripts/update_trending.py` — `main()` derives the boundary from the store's `generated_utc`; `--since <ISO8601Z>` overrides it and a malformed stamp is refused loudly.
- [x] 5. `scripts/self_correct_raw.py` — write only when the snapshot actually changed (as its own docstring always claimed) and refresh `generated_utc` when it did, so a corrected snapshot is re-merged instead of skipped as "old".
- [x] 6. `tests/test_ingest_watermark.py` (new) — the boundary, fail-open, the filename fallback, the boundary instant, the derived/`--since` CLI paths end to end, and the corrected-snapshot re-merge.
- [x] 7. `Makefile`: `tests/test_ingest_watermark.py` added to the `_test` fallback chain, so the existing "every `tests/test_*.py` runs" guard stays green.
- [x] 8. `ARCHITECTURE.md` (rule 6h): the merge targets' rows describe the incremental boundary.
- [x] 9. `AGENTS.md` §8 guard row: BLOCKED — the file is protected and the write was refused (the #212/#310 class). The row's text, the rule 3c disclosure comment on #175 and the "owed" record are written up instead, as a finding.
- [x] 10. Verified: `make lint`, `make test`, `make validate`, `make validate-mapped`, `make openspec-check`, `make architecture-check` green.
- [x] 11. `OPENSPEC.md` regenerated (`make openspec-index`).
- [x] 12. `findings.md` written for the gap found while working (a raw edited in place by the fix prompt, not `self_correct_raw`, is not re-admitted); `make findings-check` green.
