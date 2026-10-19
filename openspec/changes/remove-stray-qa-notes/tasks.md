# Tasks

- [x] 1. The tracked change exists (this directory) before any code edit
- [x] 2. `qa-report.txt.notes` removed from the tracked tree (`git rm --cached`, working copy deleted)
- [x] 3. `tests/test_fix_loop.py::test_no_scratch_report_file_is_tracked` asserts nothing in the scratch class is tracked
- [x] 4. The guard verified RED with the file restored and GREEN after the removal
- [x] 5. `OPENSPEC.md` regenerated; `openspec-index-check` and `check_openspec_tasks` green
- [x] 6. `make lint`, `make test`, `make openspec-check` and `make architecture-check` green
