# fleet-lifecycle

## ADDED Requirements

### Requirement: The issue thread owns the PR-to-reviewer handover

Every lane MUST record the whole lifecycle on the issue's own thread, not only in a
PR or a chat message: a signed `working on` claim, a PR-opened comment naming the
PR and its base sha, and a signed `done` comment whose `handover` names the ONE lane
that owns the next step. The reviewer MUST answer on that same issue thread with a
signed `reviewing` / `done` comment, and the implementer MUST keep the issue as the
follow-up thread for every fix. A PR comment alone is never the handover.

#### Scenario: the implementer opens a PR and hands it to the reviewer

- **Given** a lane claimed issue #1209 with a `working on` comment and opened PR #1210
- **When** the implementer finishes the branch
- **Then** the issue thread carries a `done #1209 · handover tll-reviewer` comment
  naming the PR and the fetched base sha, and the PR comment names the issue and the
  same next lane
- **Test:** tests/test_fleet_lifecycle.py::test_every_lane_carries_the_pr_handover_shapes

#### Scenario: the reviewer answers on the issue

- **Given** a `handover tll-reviewer` comment on an issue
- **When** the reviewer starts and finishes its review
- **Then** it posts a signed `reviewing #<id>` and a `done #<id> · handover` comment on
  that same issue, naming either `tll-implementer` for fixes or `owner` for a decision
- **Test:** tests/test_fleet_lifecycle.py::test_reviewer_shapes_are_in_the_rulebook

### Requirement: Host lane behaviour is checked against fetched upstream master

`make fleet-host-sync-check BASE=<sha>` MUST compare every host lane's `SOUL.md`,
skill and rendered `config.yaml` with the blobs at the FETCHED base (never the
working tree) and with the rulebook's tll-behaviour markers. It MUST refuse a stale
or unresolvable base, a missing profile and any divergence, naming the lane and the
file.

#### Scenario: a synced host passes against the fetched base

- **Given** a scratch profile home copied from `agents/` at HEAD and a base resolving
  to that same tree
- **When** `fleet_host_sync_check.py` runs with `--base` and that profiles home
- **Then** it exits 0 and prints the base and the lane count
- **Test:** tests/test_fleet_lifecycle.py::test_real_seam_accepts_a_synced_home

#### Scenario: a stale host is refused

- **Given** a scratch profile home where one lane's `SOUL.md` is a byte short
- **When** the same real seam runs
- **Then** it exits non-zero and names the lane and the file
- **Test:** tests/test_fleet_lifecycle.py::test_real_seam_refuses_a_diverged_soul

### Requirement: The guard runs on PRs and on push to master

The repo-side guard MUST be reachable from `make test` and `make lint`, and both
`qa-validate`'s PR path and its push path MUST reach those targets, so a change that
drops the lifecycle protocol or its test goes red in CI.

#### Scenario: CI runs the guard on both events

- **Given** `qa-validate.yml` with its `pull_request` and `push` triggers
- **When** the wiring guard scans the workflow and the Makefile
- **Then** both events reach `make test` (which runs the new module) and neither
  workflow reaches `scripts/` directly
- **Test:** tests/test_fleet_lifecycle.py::test_ci_wires_the_guard_on_pr_and_push
