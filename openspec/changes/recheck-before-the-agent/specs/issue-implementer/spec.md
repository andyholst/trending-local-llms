# issue-implementer

## ADDED Requirements

### Requirement: The issue's state is re-read immediately before the agent starts

The implement job MUST re-read the picked issue's state in the step directly before
`Implement the issue`, after the checkout, and MUST publish `closed=true` when the issue is
closed so that no implementing, verdict, salvage, reporting or fail-loud step runs.

#### Scenario: the issue closed while the run was setting up

- **Given** the shipped `implement` job and its step list
- **When** the workflow is read
- **Then** a `make issue-state` step exists at index `impl-1`, after the checkout, and
  `Implement the issue` / `Apply the implementer's verdict` / `Did the agent leave work
  behind?` / the fail-loud step are gated on `steps.recheck.outputs.closed != 'true'`
- **Test:** tests/test_workflows.py::test_the_issue_is_re_read_right_before_the_agent_starts

#### Scenario: a closed issue is a GREEN no-op with a comment

- **Given** the re-read step's `run:` block
- **When** `make issue-state` exits 4
- **Then** it comments on the issue and publishes `closed=true`
- **Test:** tests/test_workflows.py::test_the_issue_is_re_read_right_before_the_agent_starts

#### Scenario: an unreadable state is never a pass

- **Given** the same step
- **When** `make issue-state` exits 2
- **Then** it fails with `::error::` and does not publish `closed=false`
- **Test:** tests/test_workflows.py::test_the_issue_is_re_read_right_before_the_agent_starts
