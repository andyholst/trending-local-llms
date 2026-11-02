# Tasks

- [x] 1. The tracked change exists (this dir) before any code edit
- [x] 2. `update_trending.load_store()` is the one load seam: reads catalog + measurements + posts and returns `flatten_store(...)`; falls back to the flat store when the split files are absent
- [x] 3. `main()` writes `data/models.json` as the catalog (no inline `engines[]`) alongside the already-written measurements.json + posts.json; the flat snapshot stays the oracle
- [x] 4. `data/model_contract.json` relaxes `engines` from required; the top-level `engines` registry is unchanged
- [x] 5. `validate.main()` loads through `load_store()` so every wired check keeps reading the same flat in-memory store
- [x] 6. `check_split_flatten` still proves shipped split files == split(flat view) and nothing is lost (the #463/#525/#411/#650 guard)
- [x] 7. Engine support-surface (#338) reads the same flattened store
- [x] 8. tests/test_measurements_split.py NEW module: (a) catalog has no inline engines, (b) engagement resolved once from posts.json, (c) flatten == old inline guarded by check_no_value_loss, (d) renderer materialises catalog x measurements with unchanged ranking, (e) support-surface reads same store — real logic, no mocks, E2E companion per external-call mock
- [x] 9. tests/test_split_store.py updated so fixtures read through the same split/flatten round-trip
- [x] 10. `README.md` byte-identical; `make lint`, `make test`, `make validate` (data/schema) and `make openspec-check` green
- [x] 11. `OPENSPEC.md` regenerated; `openspec-index-check` and `check_openspec_tasks` green
- [x] 12. Commits authored `Andy Holst <andy.holst@protonmail.com>`; `make lint-fix` run before commit so the first CI `validate` is not red on trailing newlines
