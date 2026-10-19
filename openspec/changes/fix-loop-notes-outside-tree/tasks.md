# Tasks

- [x] 1. The tracked change exists (this directory) before any code edit
- [x] 2. `scripts/fix_loop.sh` keeps its between-round notes in a `mktemp` file outside the checkout and removes it on exit
- [x] 3. `.gitignore` covers the `qa-report.txt.*` class, not two exact names
- [x] 4. `tests/test_fix_loop.py::test_scratch_notes_stay_out_of_the_tree` drives the REAL loop with the production report path and a timed-out round
- [x] 5. `tests/test_workflows.py::_run_push_step` plants `qa-report.txt.notes` and fails when it reaches the pushed commit
- [x] 6. Both guards verified RED against the pre-change `.gitignore` + `scripts/fix_loop.sh`
- [x] 7. The `AGENTS.md` §8 guard row (rule 6c) is owed: the file is protected, so it is filed as its own `tech-debt` issue instead of edited here
- [x] 8. `OPENSPEC.md` regenerated; `openspec-index-check` and `check_openspec_tasks` green
- [x] 9. `make lint`, `make test`, `make validate`, `make architecture-check` and `make openspec-check` green
