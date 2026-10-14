# lint-linefeeds

## ADDED Requirements

### Requirement: Every tracked text file ends with a newline

`make lint` MUST fail closed when a tracked text file does not end with a newline,
naming every file, and `make lint-fix` MUST append exactly one newline to each
(idempotent). The file set MUST be what git tracks (`git ls-files`), so an ignored
or generated file can never fail the lint and a newly added file is covered at
once. A binary file (a NUL byte in its first 8000) and an empty file MUST never be
reported.

WHEN a text file is committed without a final newline,
THEN `make lint` exits non-zero and names it, and `make lint-fix` repairs it.

#### Scenario: a missing final newline is reported

- **Given** a tracked text file whose final newline was stripped
- **When** `make lint` runs
- **Then** it exits non-zero, names the file and points at `make lint-fix`
- **Test:** `tests/test_lint_linefeeds.py::test_missing_newline_is_reported_and_named`

#### Scenario: the repair is exact and idempotent

- **Given** a file without a final newline and a file that already has one
- **When** `make lint-fix` runs twice
- **Then** exactly one newline is appended to the first, the second is untouched, and the second run repairs nothing and exits 0
- **Test:** `tests/test_lint_linefeeds.py::test_fix_appends_one_newline_and_is_idempotent`

#### Scenario: binary, empty and untracked files are not findings

- **Given** a committed binary file, an empty file and an untracked scratch file
- **When** the lint runs
- **Then** none of them is reported (only the tracked text file that is really missing its newline)
- **Test:** `tests/test_lint_linefeeds.py::test_binary_and_empty_files_are_not_findings`, `tests/test_lint_linefeeds.py::test_untracked_file_is_not_a_finding`

#### Scenario: a CRLF-only ending is a finding

- **Given** a tracked file whose final byte is CR, not LF
- **When** the lint runs
- **Then** it is reported — the last byte is not a newline
- **Test:** `tests/test_lint_linefeeds.py::test_crlf_only_file_is_reported`

#### Scenario: the repository's own tree is green

- **Given** this repository after the repair
- **When** `make lint` runs on it
- **Then** it exits 0 — the gate is green on the tree it ships
- **Test:** `tests/test_lint_linefeeds.py::test_real_repo_ends_with_newlines`

### Requirement: The gate runs where a change is judged

`make lint` MUST be the first step of `qa-validate`'s `validate` job, the first
check in `scripts/fix_loop.sh`, and covered by `make test` through
`tests/test_lint_linefeeds.py` — a gate no pipeline executes is a defect (rule
6d), and the bots must repair a missing newline like any other red check.

WHEN a PR is opened or a fix round runs,
THEN a tracked file without a final newline turns the PR or the round red.

#### Scenario: CI, the loop and the suite all run it

- **Given** the PR pipeline definition, `scripts/fix_loop.sh` and the Makefile
- **When** their wiring is read
- **Then** the `validate` job runs `make lint`, the fix loop's check list starts with `lint`, and `make test` runs `tests/test_lint_linefeeds.py`
- **Test:** `tests/test_lint_linefeeds.py::test_wired_into_make_ci_the_loop_and_the_suite`

### Requirement: The editor carries the same rule

`.editorconfig` MUST state `insert_final_newline = true` with LF line endings, so
the editor enforces what CI enforces and what `make lint-fix` repairs for a file
that arrived from a bot, an upstream paste or a container write.

WHEN a file is written in an editor that honours `.editorconfig`,
THEN it ends with a newline and CI has nothing to repair.

#### Scenario: the editor half is present

- **Given** the repository root
- **When** `.editorconfig` is read
- **Then** it sets `insert_final_newline = true` (and `end_of_line = lf`), and the wiring test fails when either is removed
- **Test:** `tests/test_lint_linefeeds.py::test_wired_into_make_ci_the_loop_and_the_suite`
