## ADDED Requirements

### Requirement: An R marker names the PR it belongs to

`watch_monitor` SHALL resolve each changed workflow run to its pull request and append that
PR number to the `R:` marker as an optional trailing field. A run with no pull request SHALL
keep the existing marker shape.

#### Scenario: A PR run's marker carries its PR number

- **Given** a run row whose `pull_requests` is `[{"number": 1289}]`
- **When** the run changes state
- **Then** the marker is `R:<id>:<status>:<conclusion>:<workflow>:1289`
- **Test:** tests/test_watch_monitor.py::test_r_marker_carries_its_pull_request

#### Scenario: A push run keeps the run-only shape

- **Given** a run row with no `pull_requests`
- **When** the run changes state
- **Then** the marker carries no trailing PR field
- **Test:** tests/test_watch_monitor.py::test_r_marker_carries_workflow_name

#### Scenario: The PR field survives the workflow field

- **Given** a run that names its workflow and its PR
- **When** the marker is built
- **Then** the workflow token and the PR number are both present and colon-free
- **Test:** tests/test_watch_monitor.py::test_r_marker_carries_its_pull_request
