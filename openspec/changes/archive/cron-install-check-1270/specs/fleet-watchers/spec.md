## ADDED Requirements

### Requirement: Host trigger installation is verifiable offline

The system SHALL provide `make cron-install-check`, which reads the host's cron jobs file and FAILS when either the no-agent watchdog or the monitor-gated agent job is missing, disabled, lacks a workdir, shares a state file with the other, lacks an explicit `gh` path fix, or does not call the repo-owned detector with C/R/M markers.

#### Scenario: Complete installation
- **WHEN** both jobs are enabled with separate wrappers/state and the detector has C/R/M markers
- **THEN** the check prints `[cron-install] OK` and exits 0

#### Scenario: Silent-drift installation
- **WHEN** the watchdog is disabled or the agent's monitor gate is removed
- **THEN** the check names the gap and exits non-zero
