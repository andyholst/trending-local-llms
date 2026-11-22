## ADDED Requirements

### Requirement: A 0-job action_required head is a never-started run, not a red gate

The rulebook SHALL tell every lane that a PR head whose newest qa-validate run
is `action_required`, whose job list is empty, and whose actor is
`github-actions[bot]` is the #1115 ghost shape. The lane SHALL post one FAILURE
REPORT on the issue thread with the exact run URL and the first evidence before
any fix.

#### Scenario: A bot-pushed head has no jobs

- **Given** a rebased head with a newest run in `action_required` and zero jobs
- **When** a lane reads the run with `gh run view <id> --json jobs`
- **Then** AGENTS.md §7b names that shape as a never-started run and requires an issue-thread FAILURE REPORT before any fix
- **Test:** tests/test_fleet_handover_protocol.py::test_rulebook_carries_ghost_run_handoff

#### Scenario: The recovery is own-branch only and verified by jobs

- **Given** the lane owns the PR branch and has posted the FAILURE REPORT
- **When** it retriggers with an owner-git-identity empty commit
- **Then** AGENTS.md §7b requires verification that the new run has jobs and forbids touching another lane's branch without a signed handover
- **Test:** tests/test_fleet_handover_protocol.py::test_rulebook_carries_ghost_run_handoff

### Requirement: The guard row names the test that locks the rule

AGENTS.md §8 SHALL carry a row for this regression that names
`tests/test_fleet_handover_protocol.py` and the make target that runs it.

#### Scenario: The rulebook loses the guard row

- **Given** the current AGENTS.md §8 table
- **When** the protocol test checks its rows
- **Then** the absence of the row naming this module is a loud failure
- **Test:** tests/test_fleet_handover_protocol.py::test_rulebook_carries_ghost_guard_row
