# bot-coordination

## ADDED Requirements

### Requirement: A finished issue is not a failed run

When the implementer produced no implementation, the run MUST ask whether the issue still needs
doing, and MUST end GREEN (with a comment on the thread) when it is closed, RED when it is open or
when the state cannot be read.

#### Scenario: closed while the run was in flight

- **Given** an issue a merged PR closed during the run, and a verdict of `implement`
- **When** the final step runs `make issue-state`
- **Then** it exits 4, the run is GREEN, and ONE comment records that the issue was closed mid-run
- **Test:** tests/test_workflows.py::test_the_fail_loudly_step_asks_whether_the_issue_still_needs_doing

#### Scenario: still open, nothing implemented

- **Given** an open issue with no implementation
- **When** the final step runs
- **Then** the run is RED, exactly as before
- **Test:** tests/test_workflows.py::test_the_fail_loudly_step_asks_whether_the_issue_still_needs_doing

#### Scenario: the state cannot be read

- **Given** a `gh` that fails
- **When** `make issue-state` runs
- **Then** it exits 2 and the run is not excused
- **Test:** tests/test_issue_triage.py::test_the_state_check_tells_a_finished_issue_from_a_failed_run
