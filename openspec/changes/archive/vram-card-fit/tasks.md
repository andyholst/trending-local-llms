# Tasks

- [x] 1. Write the proposal + spec for the card-fit view (issue #337).
- [x] 2. `scripts/update_trending.py`: the ONE fit implementation — `fits_tier` / `weights_gb` / `card_memory_gb` / `tier_measurements` / `tier_rows` / `vram_need`, `CARD_TIERS_GB`, `LOW_END_TIERS_GB` (8-24 GB = a gaming laptop).
- [x] 3. `scripts/update_trending.py`: `_DATACENTER_HW` gains `b300` (a bare B300 passed `in_scope()` and earned `speed +11`).
- [x] 4. `scripts/update_trending.py`: render the `## 🖥️ Pick your card` section with an anchor index, one block per tier, evidence tags and a loud collection gap for an empty tier; most-loved per-backend best = **in-scope** best; VRAM cell = `vram_need()` with its evidence.
- [x] 5. `data/model_contract.json` + `data/search_contract.json` + `data/MODEL_CONTRACT.md`: OPTIONAL per-measurement `weight_gb` / `context_tokens` / `system_ram_min` / `storage_offload` (additive, never required).
- [x] 6. `Makefile`: `DIM_ASK` asks for the per-measurement footprint; the search prompts carry the gaming-PC card queries; `_test` runs the new guard.
- [x] 7. `scripts/update_trending.py` + `scripts/smoke_search.py`: the low-end card queries, identical in both (the smoke list must match the prompts verbatim).
- [x] 8. `scripts/validate.py`: `check_card_tables` registered in the `readme` stage; `check_readme_measurements` expects the in-scope best and the least-VRAM cell.
- [x] 9. `tests/test_card_fit.py` (50 checks) wired into `make _test`: the ladder, the datacenter gate, Apple/CPU exclusion, `vram_need`, the rendered section, the guard falsified by a dropped row.
- [x] 10. `README.md` regenerated from the store (the generator's own output).
- [x] 11. `AGENTS.md` (§5b layout, §5 scope gate, §4 optional keys, §8 guard row) and `skills/gather-data.md` (per-measurement dimensions + the low-end cards).
- [x] 12. `OPENSPEC.md` index refreshed (`make openspec-index`).
- [x] 13. `findings.md` written and `make findings-check` green (analysis ships issues, never code).
- [x] 14. Gates green: `make lint`, `make test`, `make validate`, `make validate-mapped`, `make architecture-check`, `make openspec-check`.
- [x] 15. Commit, push, open the PR (`closes #337`) — reviewable, never a draft, never merged here.
