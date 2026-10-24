# pr-body-composition

## ADDED Requirements

### Requirement: The implementation PR body is composed by a target, not spelled in a workflow

The issue-bot's implementation PR body MUST be produced by `scripts/pr_body.py` through
`make pr-body ISSUE=<n> [BRANCH=<branch>]`, so the text GitHub parses for the closure can be
rendered locally, run by a test, and read by `make pr-closure`. The workflow MUST redirect that
target's stdout into the body file and hand the file to `gh pr create --body-file`; it MUST NOT
carry the body as a heredoc or append the closing keyword itself.

#### Scenario: the composed body closes exactly the issue it implements

- **Given** a branch `ci/data-gap-287-…` and the composer asked for issue 287
- **When** the body is rendered and handed to `scripts/pr_closure.py`
- **Then** the closure check reports no problems and the only binding is `(287, [287])`
- **And** the body names the issue and the branch it was opened from
- **Test:** `tests/test_pr_body.py::test_the_composed_body_closes_exactly_the_issue_it_implements`

#### Scenario: a branch that implements another issue is refused

- **Given** a body that would close #287 and a branch that encodes #376
- **When** the composer renders it (or the CLI runs with those arguments)
- **Then** it refuses with a non-zero exit and says why on stderr
- **And** its stdout stays empty, so the workflow's redirect cannot write a half-body
- **Test:** `tests/test_pr_body.py::test_a_branch_that_implements_another_issue_is_refused`

#### Scenario: the shipped step composes the body through the target

- **Given** the "Open the PR" step of `.github/workflows/issue-bot.yml`
- **When** its `run:` block is read
- **Then** it calls `make … pr-body` and hands `--body-file pr-body.md` to `gh pr create`
- **And** it carries no heredoc body and no `printf` closing keyword of its own
- **Test:** `tests/test_pr_body.py::test_the_issue_bot_step_composes_the_body_through_the_target`

### Requirement: The body the workflow really hands to `gh` is closure-correct

The shipped step MUST be executable as written (only the external `gh` stubbed) and the body it
produces MUST close exactly the issue its branch implements. Make's recipe echo and directory
banner MUST NOT reach the body file.

#### Scenario: the executed step hands a closure-correct body to gh

- **Given** the real step executed in the checkout with a stub `gh`
- **When** the stub receives `--body-file pr-body.md`
- **Then** that file is non-empty, names the issue, ends with `Closes #<n>`, and passes
  `scripts/pr_closure.check`
- **And** no `python3 scripts/pr_body.py …` recipe line and no make directory banner appear in it
- **Test:** `tests/test_pr_body.py::test_the_shipped_step_hands_a_closure_correct_body_to_gh`

#### Scenario: the make wrapper adds nothing to the body

- **Given** `make --no-print-directory pr-body ISSUE=287 BRANCH=…`
- **When** its stdout is captured
- **Then** it starts with `Implements #287` and contains no recipe line
- **And** a call with no `ISSUE` fails with a usage message instead of composing a body for issue 0
- **Test:** `tests/test_pr_body.py::test_the_target_prints_the_body_and_a_missing_issue_is_a_usage_error`
