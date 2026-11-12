# Tasks: engine-min-version-phrasings

- [ ] Add `test_engine_min_version_detector_sees_the_build_phrases_posts_use` and prove it RED on the current detector
- [ ] Widen the `engine_min_version` `text` pattern in `scripts/data_gap_analysis.py` (old alternatives kept, per-field matching)
- [ ] New test green and `make test` green end to end
- [ ] Real-store check: the builds #214's captures state are reported as prose claims, and `make data-gaps` names them
- [ ] AGENTS.md §8 row for the new guard; `make openspec-check`, `make lint`, `make validate` green
