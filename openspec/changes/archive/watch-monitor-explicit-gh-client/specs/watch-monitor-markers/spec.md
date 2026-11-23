## ADDED Requirements

### Requirement: `fetch_payload` uses one `gh` client for every leg

`watch_monitor.fetch_payload` SHALL pass the caller-supplied `client` to every external `gh`
invocation it makes — the comment queries, the branch→PR resolution and the final master read.
It SHALL NOT replace that client with a second `gh_client()` lookup part-way through the tick.
Both cron wrappers pin an absolute `--gh` path because the stripped cron PATH cannot resolve
`gh` on its own, and the detector's own `gh_client()` fallback is only sound as the caller's
default, never as a mid-function substitution.

#### Scenario: Resolution and the master read stay on the pinned client

- **Given** `fetch_payload("o/r", <explicit stub>)`, no `gh` on PATH and `TLL_GH` naming a second stub, and a `workflow_runs` payload with one `pull_request` run whose `pull_requests` is empty and whose `head_branch` is resolvable
- **When** `fetch_payload` completes the tick
- **Then** the sentinel stub records no invocation, the explicit stub records the `pr list` resolution, and the run row carries the resolved `pull_requests`
- **Test:** tests/test_watch_monitor.py::test_fetch_payload_keeps_the_explicit_gh_client

#### Scenario: The guard fails on the pre-change seam

- **Given** the pre-fix `fetch_payload` that reassigns `client = gh_client()` inside the resolution branch
- **When** `tests/test_watch_monitor.py::test_fetch_payload_keeps_the_explicit_gh_client` runs against it with no `gh` on PATH and `TLL_GH` naming the sentinel
- **Then** the test fails because the sentinel is invoked for `pr list` (and the subsequent `commits/master` read), and it passes once the reassignment is removed
- **Test:** tests/test_watch_monitor.py::test_fetch_payload_keeps_the_explicit_gh_client
