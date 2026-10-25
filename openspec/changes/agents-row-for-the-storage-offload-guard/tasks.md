# Tasks

- [ ] 1. The owed guard is derived from the tree, not guessed: #364 is `openspec/changes/data-gap-storage-offload`, whose tasks 4/5 name the two `test_storage_offload_*` guards, and no §8 row names them
- [ ] 2. The tracked change exists (this directory) before the `AGENTS.md` edit
- [ ] 3. `tests/test_agents_rows.py` pins the row: both guards named, the module named, and the guards proved to live in it — RED against the pre-change `AGENTS.md`
- [ ] 4. `AGENTS.md` §8 carries the row beside the #163 `engine_min_version` row, naming both guards and what they catch
- [ ] 5. The pin is GREEN after the edit, and §8 still parses as a table
- [ ] 6. `make openspec-index` regenerated; `OPENSPEC.md` lists this change with issue #369
- [ ] 7. `findings.md` written (rule 6g); no finding fixed here
- [ ] 8. `make lint`, `make test`, `make validate`, `make validate-mapped`, `make architecture-check`, `make openspec-check` green
