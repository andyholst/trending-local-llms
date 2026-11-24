# Spec delta: dispatch-guard (dispatch-guard-thread-claims-1569)

## ADDED Requirements

### Requirement: An ACTIVE working-claim on the issue thread collides across hosts

The dispatch guard SHALL read the issue's comments (live through `gh api`, or a recorded
thread supplied offline) and SHALL refuse a dispatch when ANOTHER host holds a NEWER ACTIVE
working-claim on that issue. It SHALL parse the signed markers `BOT <lane> · working on
#<id>` and `BOT <lane> · dispatch #<id>`, their machine line (`user@host`) and their
`createdAt`; a LATER release marker (`done`, `pr`, `reviewing`) ends the claim. The refusal
SHALL name the holding host, lane and comment id. A caller whose OWN marker is the newest
SHALL be ALLOWED to re-dispatch. Every earlier refusal — closed issue, merged bound PR,
ceiling, in-repo registry and the `--claim` overlap — SHALL keep firing unchanged, and a
claim whose host cannot be named SHALL NOT block, because the guard refuses a different,
named host rather than inventing a collision.

#### Scenario: A second host is refused with the first host's claim quoted

- **Given** a recorded thread where `asimov@omarchy` holds the newest `working on` claim on the issue
- **When** a caller on `andy@Andys-MacBook-Pro` runs `make dispatch-check ISSUE=<n>`
- **Then** it exits non-zero and the refusal names the host `asimov@omarchy`, the lane and the holding comment id
- **Test:** tests/test_dispatch_guard.py::test_cross_host_refusal_names_host_lane_and_comment

#### Scenario: A host re-dispatching an issue it already holds is allowed

- **Given** the same caller's own marker is the newest ACTIVE claim on the issue
- **When** it runs `make dispatch-check ISSUE=<n>`
- **Then** it exits 0 and reports no cross-host reason
- **Test:** tests/test_dispatch_guard.py::test_cross_host_refusal_names_host_lane_and_comment

#### Scenario: The newest claim wins and a release clears it

- **Given** a thread with an older claim, a newer claim from another lane, then a later `done`
- **When** the guard replays the markers oldest-first by `(createdAt, comment id)`
- **Then** the newest claim holds, and the later release leaves nothing active
- **Test:** tests/test_dispatch_guard.py::test_active_claim_replays_newest_wins_and_release_clears

#### Scenario: Machine lines and markers parse from recorded threads offline

- **Given** comments carrying `(host user@host)`, a leading `user@host ·` line, a `· user@host ·` span, and prose that only mentions a host
- **When** the parser reads them
- **Then** the first three are read as identity and the prose mention is not
- **Test:** tests/test_dispatch_guard.py::test_thread_markers_and_machine_lines_are_parsed

#### Scenario: The real CLI and make seam read a recorded thread

- **Given** a recorded issue payload and a recorded thread held by another host
- **When** `dispatch_guard.py --from-file … --comments-file …` and `make dispatch-check FROM_FILE=… COMMENTS_FILE=… MACHINE=…` run
- **Then** both refuse the other host naming the holder, and both allow the holding host itself
- **Test:** tests/test_dispatch_guard.py::test_cli_reads_a_recorded_thread_offline

#### Scenario: Every prior refusal still fires alongside the thread check

- **Given** a CLOSED issue, a MERGED bound PR, an over-ceiling count and an overlapping ACTIVE `--claim`, each with an other-host thread claim present
- **When** the guard evaluates each
- **Then** the earlier refusal reason is still reported and the cross-host reason is added
- **Test:** tests/test_dispatch_guard.py::test_existing_refusals_keep_firing_alongside_the_thread_check
