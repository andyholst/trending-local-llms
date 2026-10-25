# Tasks

- [ ] 1. The tracked change exists (this directory) before any edit
- [ ] 2. `AGENTS.md` §8 carries the `tests/test_data_gap_analysis.py — test_storage_offload_*` row, immediately after the #163 row it mirrors
- [ ] 3. `tests/test_agents_rows.py` pins the row (guards named, dimension named, `41/49` named), and FAILS on `git show origin/master:AGENTS.md`
- [ ] 4. `tests/test_agents_rows.py` also proves the named module defines both guards and calls them from its `main()` (rule 6d)
- [ ] 5. `python3 tests/test_agents_rows.py` and `python3 tests/test_data_gap_analysis.py` green
- [ ] 6. `make lint` green (every touched file ends with one newline, rule 6i)
- [ ] 7. `OPENSPEC.md` regenerated; `openspec-index-check` and `openspec-tasks-check` green
- [ ] 8. `make validate`, `make validate-mapped` and the deterministic suite (`scripts/run_tests.sh`) green; `make architecture-check` green (no target, job, image or script moved)
- [ ] 9. `findings.md` records what this run noticed (rule 6g)
