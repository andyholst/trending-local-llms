# issue-review-queue

## ADDED Requirements

### Requirement: The sweep announces every hold on every working sweep

The implementer's `pick` job MUST run `make issue-skip-note` on every sweep, not only when
the pick found nothing, so a sweep that takes one issue still says on every OTHER held
issue why it was skipped. The step MUST NOT be gated on the pick's output.

#### Scenario: a sweep that takes one issue still notes the holds

- **Given** the `pick` job's step list as shipped in `issue-bot.yml`
- **When** the note step's condition is inspected
- **Then** it carries no condition on `steps.pick.outputs.issue`
- **Test:** tests/test_workflows.py::test_issue_bot

#### Scenario: the note still uses the token that can comment

- **Given** the same step
- **When** its environment is inspected
- **Then** `GH_TOKEN` is `${{ github.token }}` and it runs no label or body edit
- **Test:** tests/test_workflows.py::test_issue_bot
