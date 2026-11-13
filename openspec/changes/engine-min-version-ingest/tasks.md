# Tasks

- [x] 1. The tracked change exists (this directory) before any edit.
- [ ] 2. `scripts/update_trending.py` gains `fill_engine_min_version`: scans the `quant`/`hardware` text of every incoming measurement AND of the store measurements it merges into, matches with `data_gap_analysis._ENGINE_MIN_TEXT` (imported, never re-spelled), fills a MISSING `engine_min_version` with the matched phrase verbatim, never touches any other key, and prints `[engine-build-fill] …` naming the count.
- [ ] 3. The seam is wired into `ingest_raw_snapshots` (the same call chain that runs `refuse_fabricated_engines` / `apply_engine_aliases`), so the fill happens at ingest, not in a repair round.
- [ ] 4. `tests/test_engine_min_version_ingest.py` locks all five scenarios in `specs/measurement-ingest/spec.md` (fill, precision, no-overwrite, one detector, unstructured-shrink).
- [ ] 5. Measured Done-when: `make data-gaps` on a tree with the fill applied shows `unstructured:engine_min_version` smaller than the baseline 7 (measured 2026-11-13 on c9e2786).
- [ ] 6. Verified: `make lint`, `make _test`, `make validate`, `make openspec-check`/`openspec-tasks-check`/`openspec-index-check` green on the change tree.
- [ ] 7. `findings.md` written (`make findings-check`); `OPENSPEC.md` regenerated (`make openspec-index`).
