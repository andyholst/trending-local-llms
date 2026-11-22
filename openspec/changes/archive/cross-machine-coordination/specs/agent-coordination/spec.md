# Spec delta: agent-coordination (new capability)

## ADDED Requirements

### Requirement: Cross-machine work is claimed, reported and synced on the issue thread
Every machine working the repository SHALL comment with an `agent@host` identity, claim a
shared branch before editing it, report a red gate before fixing it, transfer steps only by
signed handover, treat the issue thread as the one board, and post a status while CI or a local
verification is pending so the other machine can take the next item.

#### Scenario: an obligation is dropped from the rulebook
- **Given** AGENTS.md rule 6u loses any one of the six obligations
- **When** `tests/test_cross_machine_coordination.py` runs
- **Then** it fails naming the dropped obligation
- **Test:** tests/test_cross_machine_coordination.py

#### Scenario: CI is pending and the machine has no local edit in flight
- **Given** a pushed head with `validate`/`live-smoke` pending
- **When** the machine posts its status comment
- **Then** it names the head SHA, the pending gates and the next issue/PR it can take
- **Test:** AGENTS.md rule 6u(f) (documented behavior, no pipeline change)
