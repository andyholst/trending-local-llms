## ADDED Requirements

### Requirement: A tracker sweep cannot close a diagnosed failure without a fix

The rulebook SHALL state that a `pipeline-run-failure` issue may be closed only
when its ledger row names a merged fix PR and a collected guard test, or was
attributed through `make pipeline-failure-attribute` with proof.

#### Scenario: Later green runs are not a fix

- **Given** a diagnosed failure issue with four later green runs and no fix PR
- **When** a tracker sweep evaluates it for closure
- **Then** AGENTS.md §6b requires the issue to stay OPEN and the runs to be recorded on the thread
- **Test:** tests/test_tracker_sweep_closure_guard.py::test_rulebook_carries_sweep_closure_guard

### Requirement: The guard row names the test that locks the rule

AGENTS.md §8 SHALL carry a regression row naming this module.

#### Scenario: The rulebook loses the guard row

- **Given** the current AGENTS.md §8 table
- **When** the module checks its rows
- **Then** the absence of the row naming this module is a loud failure
- **Test:** tests/test_tracker_sweep_closure_guard.py::test_rulebook_carries_guard_row
