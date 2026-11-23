# Tasks: contract-prose-sync

- [x] Write `scripts/check_contract_prose.py` — the ONE seam (parse rows vs `properties.models.items`)
- [x] Add rows for `engine_aliases` + `measurement_model_aliases` and correct the `hf`/`engines` required cells in `data/MODEL_CONTRACT.md` (additive, rule 6b)
- [x] Register `check_contract_prose()` as stage `docs` in `scripts/validate.py`; select it in `_validate-schema` (`--only schema,docs`)
- [x] Write `tests/test_contract_prose.py` covering the four acceptance tests (real files, no mocks)
- [x] Update `ARCHITECTURE.md` §2, §6 and §8 rows (rule 6h)
- [x] Run the module, `make lint`, `make architecture-check`, `make openspec-check`, `make test`
- [x] Regenerate `OPENSPEC.md` (`make openspec-index`)
