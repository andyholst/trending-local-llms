# Tasks

- [x] 1. The tracked change exists (this directory) before any data edit
- [x] 2. `data/models.json` carries a structured `engine_min_version` for the models whose captured source post states a build or the required flags (14 added; 25 of 38 now carry one)
- [x] 3. Every added value is the source post's own wording — verified token-by-token against `data/raw/*.json`
- [x] 4. `tests/test_data_gap_analysis.py::test_engine_min_version_backfill_traces_to_the_captured_source_text` locks the traceability (version tokens + a distinctive token present in the captured text) and refuses an invented value
- [x] 5. `tests/test_data_gap_analysis.py::test_engine_min_version_coverage_can_never_shrink` locks a coverage floor; it FAILS on the pre-change store (11 models)
- [x] 6. The ranked `engine_min_version` gap in the analysis is smaller than the 29/30 the filed issue recorded
- [x] 7. `README.md` is unaffected (no dimension is rendered) and `check_readme_generated` stays green
- [x] 8. `findings.md` records the remaining dimensions, and the `AGENTS.md` §8 guard row this run could not write (protected file), as their own work
- [x] 9. `OPENSPEC.md` regenerated; `openspec-index-check` and `check_openspec_tasks` green
- [x] 10. `scripts/validate.py` stages `data,schema,search,mapping,removal,readme` PASS; `make architecture-check` and the deterministic suite green
