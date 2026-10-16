# pr-lifecycle

## ADDED Requirements

### Requirement: A merged PR closes the issue it implements

A PR whose branch implements an issue MUST carry a closing keyword bound to **that** issue, so the
merge closes it. GitHub binds a closing keyword to the single reference that follows it, so a
clause that chains a second reference (`Closes #271 and #276`) closes only the first and MUST be
refused rather than accepted: the second issue would stay open after a green, merged change, and
the shared bot queue would offer that work again. The rule has exactly ONE implementation,
reachable from a `make` target CI runs (rules 6d/6m).

WHEN a PR is validated,
THEN the issue its branch implements is bound by its own closing keyword, or the check exits
non-zero naming the branch and the issue that would stay open.

#### Scenario: a chained reference is refused

- **Given** a body containing `Closes #271 and #276` — the measured PR #272 shape
- **When** the check runs for a branch that implements #271
- **Then** it exits 1, names #276, and says only the first reference binds
- **Test:** `tests/test_pr_closure.py::test_a_chained_reference_closes_only_the_first_issue`

#### Scenario: one closing keyword per issue passes

- **Given** the same PR body written as `Closes #271` and `Closes #276` on their own lines
- **When** the check runs
- **Then** it exits 0
- **Test:** `tests/test_pr_closure.py::test_a_chained_reference_closes_only_the_first_issue`

#### Scenario: the branch's issue must be closed

- **Given** a PR on `ci/data-gap-266-storage-offload-31-models` whose body only *mentions* #266
- **When** the check runs
- **Then** it exits 1, because a bare reference is not a closing keyword and the issue would stay
  open
- **Test:** `tests/test_pr_closure.py::test_the_branch_issue_must_be_closed_by_its_own_keyword`

### Requirement: A PR closes only the issues it implements

A PR whose branch implements no issue MUST NOT carry a closing keyword: `refresh-bot`'s refresh PR
*references* its tracking issue, it does not close it. Carrying a closing keyword for an unrelated
issue (measured: `Closes #1`, the long-closed CI meta issue) means the refresh could close an issue
it does not implement.

WHEN a PR whose branch encodes no issue is validated,
THEN a closing keyword in its body is refused and the body's plain reference form is accepted.

#### Scenario: the refresh PR does not close the meta issue

- **Given** the refresh PR body and a branch `ci/trending-refresh-<UTC>`
- **When** the check runs with `Closes #1` in the body
- **Then** it exits 1 and says a PR that implements no issue must not close one
- **Test:** `tests/test_pr_closure.py::test_a_refresh_pr_must_not_close_the_meta_issue`

#### Scenario: the shipped refresh body references instead of closing

- **Given** `.github/workflows/refresh-bot.yml`
- **When** its PR body is inspected
- **Then** it carries `Refs #1` and no `Closes #1`
- **Test:** `tests/test_pr_closure.py::test_a_refresh_pr_must_not_close_the_meta_issue`

#### Scenario: a refresh branch implements no issue

- **Given** the branch `ci/trending-refresh-20261016-1200`, whose trailing digits are a timestamp
- **When** the implemented issue is derived
- **Then** it is none, so the refresh PR can never be held to closing one
- **Test:** `tests/test_pr_closure.py::test_the_branch_encodes_the_issue_the_slug_may_not_confuse`

#### Scenario: a closing keyword quoted as code is not a claim

- **Given** a body whose only `Closes #12` sits inside a fenced block or an inline code span — the
  measured shape of this change's own PR
- **When** the check runs
- **Then** no binding is reported, so the PR is refused for not closing its issue (GitHub likewise
  links nothing inside code: `closingIssuesReferences` came back empty), and the same body WITH a
  real closing line passes
- **Test:** `tests/test_pr_closure.py::test_code_quotes_the_rule_it_does_not_make_a_claim`

### Requirement: The check reads the payload by path and runs on every PR

The check MUST read the head branch and the body from the webhook payload **by path**, never
interpolated into a workflow `run:` block, and it MUST run on every PR — a guard nothing executes is
not a guard (rule 6d). A non-PR event (a push to `master`, a dispatch) is a green no-op, so the same
job can run on every trigger.

WHEN `qa-validate`'s `validate` job runs,
THEN it invokes the check through the Makefile, which reads `$GITHUB_EVENT_PATH` itself.

#### Scenario: the payload is read by path, not interpolated

- **Given** `.github/workflows/qa-validate.yml`'s `validate` job
- **When** its steps are inspected
- **Then** one step runs `make pr-closure` and no `${{ github.event.pull_request.body }}` appears in
  the run block
- **Test:** `tests/test_pr_closure.py::test_the_pipeline_runs_it_on_every_pr`

#### Scenario: a push event is a green no-op

- **Given** a payload with no `pull_request` (a push to `master`)
- **When** the CLI runs against it
- **Then** it exits 0 and says there is nothing to check
- **Test:** `tests/test_pr_closure.py::test_the_cli_reads_the_webhook_payload_by_path`
