## ADDED Requirements

### Requirement: The monitor emits only changes

The monitor SHALL compare fetched comment IDs, CI run states and the master head SHA against a caller-owned state file and emit only changed markers, never timestamps.

#### Scenario: A quiet tick

- **Given** an unchanged set of comments, runs and master head
- **When** the monitor runs
- **Then** it emits no marker lines and no timestamps
- **Test:** tests/test_watch_monitor.py::test_quiet_tick_emits_nothing

### Requirement: A merge wakes the fleet to sync

A changed master head SHALL emit an `M:<sha>` marker so the watcher fetches/pulls and re-syncs the rulebook and skills.

#### Scenario: PR merged to master

- **Given** a previous monitor state with an older master SHA
- **When** the new head differs
- **Then** exactly one `M:` marker is emitted and the rulebook names fetch/pull + skill sync as the first action
- **Test:** tests/test_watch_monitor.py::test_master_merge_marker_and_rulebook_duty

### Requirement: The rulebook owns the two-job protocol

`AGENTS.md` SHALL name the no-LLM monitor job and the monitor-gated agent job, and the §8 guard SHALL fail when either is removed.

#### Scenario: Guard against a dropped protocol

- **Given** the rulebook with rule 6w removed
- **When** the guard runs
- **Then** it fails loudly
- **Test:** tests/test_watch_monitor.py::test_rulebook_carries_two_job_watch_protocol
