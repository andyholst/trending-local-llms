# Tasks

- [x] 1. Write the proposal + GWT capability spec for issue #708 (`models-order-matches-readme`: reorder data/models.json to the README 'Most loved' order + add a guard).
- [x] 2. Confirm the defect: `models.json` models order != README "Most loved" order at 24 positions on master (introduced by #695); pre-#695 clean. Reproduced and measured (24 divergences, sets equal, 117 rows).
- [x] 3. Derive the canonical order from the README "Most loved" table (`readme_order` regex `^| [**(.+?)**]`, same as llgenie `sync_registry.check_readme_matches`).
- [x] 4. `data/models.json` — reorder `models[]` to the README "Most loved" order: pure positional (41/41 add/del), id + content multiset verified identical, no value lost/added.
- [x] 5. Verify canonicality: `scripts/update_trending.py --render-only` produces no README diff (the reordered store is the canonical render source).
- [x] 6. `scripts/validate.py` — add `_MOST_LOVED_HDR` + `check_models_order_matches_readme(store)` (mirrors the llgenie contract) and register it under the `data` stage.
- [x] 7. `tests/test_validate.py` — `test_models_order_matches_readme` runs the REAL check: committed README vs real store passes (0 divergences), a temp README with two 'Most loved' rows swapped is caught.
- [x] 8. Verify: `scripts/validate.py --only data,schema,removal` QA PASSED (incl. additive-only, split/flatten, schema green; the new guard reports 0 divergences); `test_validate.py` PASSED 182/0.
- [x] 9. `OPENSPEC.md` regenerated (`models-order-matches-readme` active); `make openspec-check` green; `make lint` clean (all committed files end in a newline); commit authored `Andy Holst <andy.holst@protonmail.com>`.
