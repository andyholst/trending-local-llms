# bot-commit-safety

## ADDED Requirements

### Requirement: The working files are unstaged from ONE list

Both bots MUST unstage their working files through `make reset-working-files`, which reads
`scripts/issue_bot_working_files.txt`. `make check-working-files` MUST fail when a name on that
list is not gitignored.

#### Scenario: a listed scratch file is staged and the real change is not touched

- **Given** a repository where `issue.md` and `real.txt` are staged
- **When** `scripts/reset_working_files.py` runs
- **Then** `issue.md` is unstaged and still on disk, and `real.txt` stays staged
- **Test:** tests/test_working_file_list.py::test_it_unstages_the_list_and_keeps_the_real_change

#### Scenario: a name that is not gitignored is refused

- **Given** a list naming `findings.md` and a `.gitignore` without it
- **When** `--check` runs
- **Then** it exits 1 and names `findings.md`
- **Test:** tests/test_working_file_list.py::test_check_fails_when_a_name_is_not_gitignored

#### Scenario: every bot commit step uses the target

- **Given** the issue-bot and fix-bot workflows
- **When** their steps are read
- **Then** no step carries the literal `git reset -q --` line and three call sites use the target
- **Test:** tests/test_working_file_list.py::test_one_list_one_target
