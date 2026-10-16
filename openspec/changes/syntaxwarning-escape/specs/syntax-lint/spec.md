# syntax-lint

## ADDED Requirements

### Requirement: No tracked Python module raises a SyntaxWarning

`make lint` MUST fail closed when a tracked Python module does not compile without
a `SyntaxWarning` (and when a module does not parse at all), naming every module
and the warning it raises. The file set MUST be what git tracks (`git ls-files
'*.py'`), so an ignored, generated or untracked module can never fail the lint and
a newly added module is covered at once. The check MUST compile each module **from
source**, so a module's import side effects never run during the lint.

WHEN a tracked module carries an invalid escape sequence or another
compile-time warning,
THEN `make lint` exits non-zero and names the module and the warning.

#### Scenario: an invalid escape sequence is reported

- **Given** a tracked module with a single backslash + space in a non-raw string literal
- **When** the lint runs
- **Then** it exits non-zero, names the module and quotes the `SyntaxWarning`
- **Test:** `tests/test_lint_syntax.py::test_invalid_escape_is_reported_and_named`

#### Scenario: a clean tree is green

- **Given** a tree whose modules all compile cleanly
- **When** the lint runs
- **Then** it exits 0 and reports how many modules it checked
- **Test:** `tests/test_lint_syntax.py::test_clean_tree_is_green`

#### Scenario: an untracked module is not a finding

- **Given** an untracked module with an invalid escape
- **When** the lint runs
- **Then** it is green — the file set is `git ls-files`
- **Test:** `tests/test_lint_syntax.py::test_untracked_module_is_not_a_finding`

#### Scenario: the repository's own tree is green

- **Given** this repository after the fix to `scripts/update_trending.py`
- **When** the lint runs on it
- **Then** it exits 0 — the gate is green on the tree it ships, and the module that
  warned can never warn again
- **Test:** `tests/test_lint_syntax.py::test_real_repo_has_no_syntax_warnings`

### Requirement: The gate runs where a change is judged

The syntax lint MUST be part of `make lint` — the first step of `qa-validate`'s
`validate` job and the first check in `scripts/fix_loop.sh` — and MUST be covered
by `make test` through `tests/test_lint_syntax.py`. A gate no pipeline executes is
a defect (rule 6d), and the bots must repair a `SyntaxWarning` like any other red
check.

WHEN a PR is opened or a fix round runs,
THEN a tracked module that warns on compile turns the PR or the round red.

#### Scenario: CI, the loop and the suite all run it

- **Given** the Makefile, the PR pipeline definition and `scripts/fix_loop.sh`
- **When** their wiring is read
- **Then** the `lint` target runs `scripts/lint_syntax.py`, the `validate` job runs
  `make lint`, the fix loop's check list starts with `lint`, and `make test` runs
  `tests/test_lint_syntax.py`
- **Test:** `tests/test_lint_syntax.py::test_wired_into_make_ci_the_loop_and_the_suite`
