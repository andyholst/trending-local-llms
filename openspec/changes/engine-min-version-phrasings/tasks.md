# Tasks: engine-min-version-phrasings

- [x] Add `test_engine_min_version_detector_sees_the_build_phrases_posts_use` and prove it RED on the current detector (measured: 3 checks FAIL, `un=[] nc=[built,kv,quiet,swift]`)
- [x] Widen the `engine_min_version` `text` pattern in `scripts/data_gap_analysis.py` (old alternatives kept, per-field matching)
- [x] New test green and `make test` green end to end (data-gap suite measured 243/0; full suite green on the ticked tree)
- [x] Real-store check: the builds #214's captures state are reported as prose claims, and `make data-gaps` names them (measured: 7 ingest jobs + 4 untraceable, WARN-only scan, `make _validate-data` RC=0)
- [x] AGENTS.md §8 row for the new guard; `make openspec-check`, `make lint`, `make validate` green
