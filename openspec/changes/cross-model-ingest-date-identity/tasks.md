# Tasks

Issue: #971

- [x] 1. The tracked change exists before any code (`openspec/changes/cross-model-ingest-date-identity/`)
- [x] 2. `scripts/update_trending.py` gains the shared `cross_row_duplicate_identity(e)`
      signature — (engine, tps, date, source_post) same-post + (engine, tps, date)
      variant — used by BOTH `cross_model_carriers` / `refuse_cross_model_duplicate_measurements`
      (the ingest refusal) and `validate.cross_row_duplicate_measurements` (the #795 gate):
      one implementation, rule 6d
- [x] 3. The refusal seam keys its carriers on the date identity (never hardware), so a
      hardware-renamed duplicate ("R9700" vs "AMD R9700", same date, same post) is
      refused at ingest
- [x] 4. `CROSS_MODEL_ALLOW_LIST` re-keyed to the date identity; the documented pairs
      still resolve to the same model-id sets
- [x] 5. `scripts/validate.py::cross_row_duplicate_measurements` reads ONE shared
      `cross_row_duplicate_identity` (no second key-building copy)
- [x] 6. `tests/test_cross_model_attribution.py` gains
      `test_a_planted_hardware_renamed_duplicate_is_refused_at_ingest` and
      `test_the_refusal_reads_the_gate_identity`; existing refusal tests updated to the
      date-keyed identity
- [x] 7. `tests/test_ingest_refusal_ledger.py` cross-model copy fixture aligned to the
      date identity (and proves a hardware-renamed copy is refused)
- [x] 8. `make openspec-index` regenerated; `make openspec-check`, `make lint` (py_compile +
      newline), the cross-model suites, the data-gap suite and the engine-figure suite
      green on the exact head; no new test failure vs origin/master baseline
