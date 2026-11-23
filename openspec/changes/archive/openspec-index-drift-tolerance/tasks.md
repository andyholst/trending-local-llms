# Tasks: openspec-index-drift-tolerance

- [x] Add `MAX_OPENSPEC_INDEX_DRIFT = 25` and the shared `index_drift()` measure to `scripts/openspec_index.py`
- [x] Make `--check` WARN and exit 0 at or under the threshold, FAIL with the count above it, and still FAIL on a missing `OPENSPEC.md`; keep `--write` unchanged
- [x] Point `scripts/openspec_index_repair.py` at the same `index_drift()` / constant so a tolerated drift is still classified and repaired
- [x] Add tests for the counting rule, the exact 25/26 boundary, a count-only drift, a single changed row and a missing index; prove before/after
- [x] Adjust the auto-merge-rebase fixture expectation: a small squash-tree drift is a tolerated WARN, not a RED (issue #1415)
- [x] Regenerate `OPENSPEC.md` so the new change is listed and the index is current
- [x] Run `tests/test_openspec_index.py`, `tests/test_openspec_index_repair.py`, `make openspec-check` and the focused gates green before opening the PR
