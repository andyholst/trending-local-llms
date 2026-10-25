# Tasks

- [x] 1. Write the proposal + `bot-commit-safety` capability spec for issue #543.
- [x] 2. `scripts/issue_bot_working_files.txt` (the ONE list) and `scripts/reset_working_files.py` (unstage + `--check`).
- [x] 3. `make reset-working-files` + `make check-working-files`, with the check wired into `make lint`.
- [x] 4. All three workflow call sites route through the target; no literal reset line remains.
- [x] 5. `tests/test_working_file_list.py` against real repositories, and both step-test stubs learn the target with the fixtures carrying the list.
- [x] 6. `tests/test_workflows.py`'s old literal guard rewritten to assert the target + the list.
- [x] 7. Verified RED on `origin/master`'s tree (12 checks fail, script absent) and GREEN after (14/14; `test_workflows` 871).
- [x] 8. `findings.md` written; `make opspec-check`, `make architecture-check`, `make lint` green.
