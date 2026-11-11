# red-run-and-repair-path

## ADDED Requirements

### Requirement: A red fix loop reds the issue-bot run

The issue-bot job MUST fail when its own fix loop ended red (`steps.loop.outputs.green == 'false'`),
in a step that runs AFTER the loop and names the issue and the PR. Capturing the loop's exit code so
the outcome comment can post is fine; leaving it unacted on is not, because the run then reports
success over a PR that cannot merge.

#### Scenario: the shipped step fires exactly on a red loop

- **Given** `.github/workflows/issue-bot.yml`'s `implement` job
- **When** its steps are read
- **Then** a step exists whose condition is `steps.loop.outputs.green == 'false'`, whose body exits 1,
  and which sits after the fix-loop step
- **Test:** `tests/test_workflows.py::test_a_red_fix_loop_reds_the_run_and_reaches_fix_bot`

### Requirement: fix-bot is dispatched for an implementer's PR too

`qa-validate`'s `dispatch-fixbot` job MUST fire for a same-repo `ci/data-gap-<n>-…` PR as well as a
`ci/trending-refresh-*` one, on a failed `validate`, keeping the existing two-`fix-bot:`-commit cap.

#### Scenario: both branch families are admitted

- **Given** `.github/workflows/qa-validate.yml`'s `dispatch-fixbot` job
- **When** its `if` is read
- **Then** it names both `ci/trending-refresh-` and `ci/data-gap-`, still requires
  `failure()` on a `pull_request` from a same-repo head
- **Test:** `tests/test_workflows.py::test_a_red_fix_loop_reds_the_run_and_reaches_fix_bot`
