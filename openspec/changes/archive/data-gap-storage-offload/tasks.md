# Tasks

- [x] 1. The tracked change exists (this directory) before any data edit
- [x] 2. `data/models.json` carries a structured `storage_offload` for every model whose captured source post states one (`deepseek-v4.1-flash`)
- [x] 3. Every added value is the source post's own wording — verified token-by-token against `data/raw/*.json`
- [x] 4. `tests/test_data_gap_analysis.py::test_storage_offload_backfill_traces_to_the_captured_source_text` locks the traceability (a storage medium + every size token present in the captured text) and refuses an invented value
- [x] 5. `tests/test_data_gap_analysis.py::test_storage_offload_coverage_can_never_shrink` locks a coverage floor; it FAILS on the pre-change store (`8 models carry it` against a floor of 9)
- [x] 6. The ranked `storage_offload` gap in the analysis is smaller than the 41/49 the filed issue recorded (39 -> 38 missing; `unstructured:storage_offload` 6 -> 5)
- [x] 7. `README.md` is unaffected (the dimension is not rendered) and `check_readme_generated` stays green
- [x] 8. `findings.md` records the remaining dimensions and the two storage_offload detector defects this run found, as their own work
- [x] 9. `OPENSPEC.md` regenerated; `openspec-index-check` and `check_openspec_tasks` green
- [x] 10. `scripts/validate.py` stages PASS; `make architecture-check`, `make lint` and the deterministic suite green
