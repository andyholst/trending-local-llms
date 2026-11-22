## ADDED Requirements

### Requirement: The rulebook names a minimum claim settle window

`AGENTS.md` §7b SHALL name a minimum settle window between a wake-up and a claim, so the
wait-and-re-read race guard has a floor. The number SHALL live in ONE place,
`scripts/watch_monitor.py::CLAIM_SETTLE_SECONDS`, and the rulebook SHALL name that seam.

#### Scenario: A woken lane waits out the window before claiming

- **Given** a `C:`-marker wake-up on an issue a peer may already be claiming
- **When** the lane decides whether to claim
- **Then** it waits at least the named window and re-reads the thread before posting its claim
- **Test:** tests/test_watch_monitor.py::test_the_rulebook_names_the_claim_settle_window

#### Scenario: The floor is load-bearing in the offline contract

- **Given** `make watch-monitor --check`
- **When** it runs
- **Then** it refuses a settle floor below 60 seconds and reports the pinned window
- **Test:** tests/test_watch_monitor.py::test_the_offline_contract_pins_the_settle_floor

### Requirement: The guard pins the row and the number together

The guard SHALL fail when the rulebook needle is dropped, when the pinned number changes,
or when the seam constant and the rulebook disagree.

#### Scenario: A dropped row or pin turns CI red

- **Given** the needle absent from §7b, or the constant differing from the rulebook
- **When** the guard runs
- **Then** it FAILS naming the missing needle or the disagreement
- **Test:** tests/test_watch_monitor.py::test_the_rulebook_names_the_claim_settle_window
