## ADDED Requirements

### Requirement: The heartbeat is opt-in and deterministic

The monitor SHALL append one `H:<bucket>` marker only when `--heartbeat-seconds N` is positive, where `bucket = int(time.time()) // N`. The default `N=0` SHALL leave the quiet tick silent, and no marker SHALL carry a wall-clock timestamp.

#### Scenario: A quiet tick with no heartbeat flag

- **Given** an unchanged snapshot and the default flags
- **When** the monitor runs
- **Then** it emits no marker lines
- **Test:** tests/test_watch_monitor.py::test_quiet_tick_emits_nothing

#### Scenario: A heartbeat boundary

- **Given** `--heartbeat-seconds 900` and two timestamps in the same 15-minute bucket
- **When** the pure diff is computed for both
- **Then** the H marker is identical, and it changes at the next boundary
- **Test:** tests/test_watch_monitor.py::test_heartbeat_marker_is_deterministic

### Requirement: The heartbeat coexists with event markers

An H marker SHALL NOT suppress a simultaneous C, R or M marker, and the offline check SHALL accept H as a legal prefix.

#### Scenario: Heartbeat plus a red pipeline

- **Given** a new failed run and a positive heartbeat interval
- **When** the monitor diffs the snapshot
- **Then** both the R marker with `failure` and the H marker appear
- **Test:** tests/test_watch_monitor.py::test_heartbeat_coexists_with_failure_marker

#### Scenario: The offline contract

- **Given** the check mode with no network
- **When** `make watch-monitor CHECK=1` runs
- **Then** the contract accepts H and still refuses an unknown prefix
- **Test:** tests/test_watch_monitor.py::test_offline_check_mode

### Requirement: The rulebook owns the continue-working duty

`AGENTS.md` rule 6w SHALL name H as a work heartbeat and require the agent to continue with the oldest unclaimed actionable issue after handling C/R/M, instead of stopping at a diagnosis.

#### Scenario: Guard against a dropped duty

- **Given** the rulebook with the H marker or the continue-working sentence removed
- **When** the guard runs
- **Then** it fails loudly
- **Test:** tests/test_watch_monitor.py::test_rulebook_carries_two_job_watch_protocol
