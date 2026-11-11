# Tasks

- [x] 1. The tracked change exists (this directory) before any code edit
- [x] 2. `hardware_vram_gb()` honours an explicit `<n> GB total` over any per-card size
- [x] 3. `hardware_vram_gb()` applies a multiplier that follows the size (`32GB x8`)
- [x] 4. `_DATACENTER_HW` names AMD's datacenter V-series (v620/v520/v340), leaving Radeon Pro W-series in scope
- [x] 5. `tests/test_trend_score.py` covers both spellings, the pool being out of scope, the single V620, the W7900 staying in, and `best_in_scope()` picking the card figure
- [x] 6. The guard verified RED against the pre-change `scripts/update_trending.py` (6 failures) and GREEN after
- [x] 7. `README.md` regenerated at the store's own `generated_utc` (no merge, no snapshot, no timestamp bump) so the 125B ROCm cell shows the in-scope 60 t/s
- [x] 8. `OPENSPEC.md` regenerated; `openspec-index-check` and `check_openspec_tasks` green
- [x] 9. `make lint`, `make test`, `make validate`, `make architecture-check` and `make openspec-check` green
