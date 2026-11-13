# Tasks

- [x] 1. The tracked change exists (this directory) before any edit.
- [x] 2. `scripts/update_trending.py` gains `fill_engine_min_version`: scans the `quant`/`hardware` text of every INCOMING raw measurement, matches with `data_gap_analysis._ENGINE_MIN_TEXT` (imported, never re-spelled), fills a MISSING `engine_min_version` with the matched phrase verbatim, never touches any other key, never fills from the model's `why` prose (#470), and prints `[engine-build-fill] …` naming the count.
- [x] 3. The seam is wired into `ingest_raw_snapshots` (right after the attribution/engine refusals, before the store merge), so `merge_engines`' same-post dimension fill carries the value into the store row.
- [x] 4. `tests/test_engine_min_version_ingest.py` locks all six scenarios in `specs/measurement-ingest/spec.md` (fill, precision, no-overwrite, one detector, captured-class closes, `why` never fills). — PASSED 9 | FAILED 0 (host, tll312 venv).
- [x] 5. Measured Done-when: a full replay of ALL 990 current raw snapshots through the real `ingest_raw_snapshots` over the fetched `origin/master` store shows `captured_prose["engine_min_version"]` 11 → 0, `unstructured` 2 → 0, `not_captured` 69 → 53, measurement-level values 0 → 172, and NO model lost a key (rule 3b sanity). Numbers reported on the PR.
- [ ] 6. Verified: `make lint`, `make _test`, `make validate`, `make openspec-check`/`openspec-tasks-check`/`openspec-index-check` green on the change tree.
- [ ] 7. `findings.md` written (`make findings-check`); `OPENSPEC.md` regenerated (`make openspec-index`).

