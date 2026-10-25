# bot-commit-safety

## ADDED Requirements

### Requirement: A conflict marker is refused before it is committed

`make check-conflict-markers` MUST exit non-zero and name every path when a tracked file carries
a git conflict block, MUST ignore untracked and ignored files, and MUST skip binary files. Both
bot commit steps MUST run it before `git add -A`.

#### Scenario: a marker in a tracked file

- **Given** a repository whose `Makefile` is committed with a `<<<<<<<` / `=======` / `>>>>>>>`
  block
- **When** the guard runs
- **Then** it exits 1, names `Makefile` and the line numbers, and says a marker in a parsed file
  breaks every `make`
- **Test:** tests/test_conflict_marker_guard.py::test_a_marked_tracked_file_is_refused

#### Scenario: scratch and binary files are not findings

- **Given** a repository with a marked IGNORED file, a marked UNTRACKED file and a committed
  binary whose head carries marker-shaped bytes
- **When** the guard runs
- **Then** it exits 0
- **Test:** tests/test_conflict_marker_guard.py::test_an_ignored_or_untracked_file_does_not_fail

#### Scenario: both bots check before staging

- **Given** the issue-bot and fix-bot workflows
- **When** their commit steps are read
- **Then** each calls `make check-conflict-markers` before its `git add -A`
- **Test:** tests/test_conflict_marker_guard.py::test_the_bots_and_lint_run_the_guard
