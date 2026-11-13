# Tasks: search-contract-alias-key

- [x] `data/search_contract.json` declares the optional model-item key
      `measurement_model_aliases` (array of ids, uniqueItems, minItems 1), kept
      out of `required`; `additionalProperties: false` unchanged.
- [x] `scripts/validate.py::check_measurement_alias_map` also reads
      `data/raw/*.json` model items and refuses a dangling counterpart naming
      BOTH sides (snapshot file + raw model, counterpart id, the store); the
      store-side refusal from #652 is unchanged.
- [x] `scripts/update_trending.py` gains `merge_measurement_aliases(existing,
      incoming)` — union, deduped case-insensitively, never narrowed — called in
      the existing-row ingest path; the new-model path keeps the key via
      `normalize_model` (proved by test, not assumed).
- [x] `tests/test_measurement_attribution.py` — conforming raw snapshot through
      the search contract; new model keeps the captured exception; existing row
      gains counterparts as a union through the REAL ingest (`raw_dir=` seam).
- [x] `tests/test_validate.py` — dangling raw counterpart refused naming both
      sides; the #652 store-side test still passes.
- [x] `tests/test_measurement_attribution.py::test_alias_key_declared_in_both_contracts`
      — the pair-declaration assertion covers `measurement_model_aliases` in both
      contracts, neither `required`, same structural shape.
- [ ] `make lint`, `make test` (host suite + container), `make validate`,
      `make openspec-check`, `make architecture-check` all green; `ARCHITECTURE.md`
      §6 rows for `scripts/update_trending.py` and `scripts/validate.py` mention
      the alias union seam and the both-sides gate.
- [ ] PR opened (ready, not draft) with the message pattern + single closing
      claim; monitored to green and auto-merged.
