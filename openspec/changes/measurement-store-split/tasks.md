# Tasks

- [x] 1. The tracked change exists (this directory) before any code edit
- [x] 2. `split_store()` is the one definition of the normalised split (catalog / measurements / posts)
- [x] 3. `flatten_store()` rebuilds the flat store; counters splice back; missing post -> 0
- [x] 4. `_measurement_identity()` is the lossless identity key (counters excluded)
- [x] 5. `main()` writes data/measurements.json + data/posts.json alongside the unchanged flat models.json
- [x] 6. data/measurements_contract.json + data/posts_contract.json shipped (draft 2020-12, additionalProperties: false)
- [x] 7. validate settles check_measurements_contract, check_posts_contract, check_split_flatten under the `schema` stage, skipping when files absent
- [x] 8. tests/test_split_store.py NEW module tests the split, flatten, contracts, guard, and shipped files (all green)
- [x] 9. tests/test_make_commands.py fixture copies the new contracts (2 lines)
- [x] 10. Old data/models.json, model_contract.json, README.md and all old test modules unchanged
- [x] 11. `OPENSPEC.md` regenerated; `openspec-index-check` and `check_openspec_tasks` green
- [x] 12. `make lint`, `make test`, `make validate` (data/schema stages) and `make openspec-check` green