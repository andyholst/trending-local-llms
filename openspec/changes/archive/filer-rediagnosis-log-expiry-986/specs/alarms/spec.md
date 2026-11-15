# alarms

## ADDED Requirements

### Requirement: a still-unreadable re-diagnosis is bounded and terminates as log_expired

`make pipeline-failure-issue` MUST, on every still-unreadable re-read of an UNDIAGNOSED ledger row
in `data/pipeline_failures.json` (the two "cannot read the run" branches: `jobs unreadable again`
and `log still unreadable`), GROW the row's APPEND-ONLY `rediagnose_attempts` counter (rule 3b:
nothing removed, `undiagnosed` KEPT). After `MAX_REDIAGNOSE_ATTEMPTS` consecutive still-unreadable
sweeps it MUST stamp a TERMINAL `log_expired` state on the row (the reason, loud, once — printed as
`LOG EXPIRED run <id>: …`) and MUST exclude that row from the pending re-diagnosis set so the
pending queue drains instead of retrying a log that can never be read. The two STRUCTURAL branches
(a run naming no failed job; a readable log with no error-shaped line) MUST stay
reported-and-retried per #969, never expired. `--dry` MUST preview the stamp (`WOULD EXPIRE run
<id>: …`) and write nothing.

#### Scenario: a run that ages out of retention is stamped terminal log_expired, once

- **Given** a ledger row for run 100 carrying `undiagnosed`, no `rediagnosed_utc`, and
  `rediagnose_attempts == MAX_REDIAGNOSE_ATTEMPTS - 1`, while the stub `gh` serves the run's jobs
  and FAILS every log fetch
- **When** `scripts/pipeline_failure_issue.py` sweeps
- **Then** the row gains `rediagnose_attempts == MAX_REDIAGNOSE_ATTEMPTS`, a `log_expired` reason
  and a `log_expired_utc`, the original `undiagnosed` value remains, the sweep prints the loud
  `LOG EXPIRED run 100: …` line, and a RE-sweep no longer touches the row (no re-read, no line) —
  the pending queue drains
- **Test:** tests/test_pipeline_failure_issue.py::test_a_run_that_ages_out_stamps_log_expired_and_drains_the_queue

#### Scenario: an unreadable log that has not hit the bound stays pending with an attempt counter

- **Given** a ledger row for run 100 carrying `undiagnosed` and no `rediagnose_attempts`, while the
  stub `gh` serves the jobs and FAILS the log fetch
- **When** `scripts/pipeline_failure_issue.py` sweeps
- **Then** it exits 0, prints the loud `rediagnose run 100: log still unreadable` line, the row
  gains `rediagnose_attempts == 1` with NO `log_expired` and NO `rediagnosed_utc` — it stays
  eligible for the next sweep and no other value changed (rule 3b)
- **Test:** tests/test_pipeline_failure_issue.py::test_a_still_unreadable_log_leaves_the_row_undiagnosed_and_retries_next_sweep

#### Scenario: a structural mismatch is not counted as a retention expiry

- **Given** a ledger row for run 100 naming a job the run's job list no longer has, while the stub
  `gh` serves that job list
- **When** `scripts/pipeline_failure_issue.py` sweeps
- **Then** it reports the mismatch loudly, the row stays UNDIAGNOSED, and it gains NO
  `rediagnose_attempts` and NO `log_expired` — a structural mismatch is not a log that aged out
- **Test:** tests/test_pipeline_failure_issue.py::test_a_still_unreadable_log_leaves_the_row_undiagnosed_and_retries_next_sweep

#### Scenario: log_expired dry mode previews the stamp and writes nothing

- **Given** a ledger row for run 100 at the attempt bound and a stub `gh` whose log fetch fails
- **When** `scripts/pipeline_failure_issue.py` sweeps with `--dry`
- **Then** it exits 0, prints `WOULD EXPIRE run 100: …`, and the ledger file is byte-identical
- **Test:** tests/test_pipeline_failure_issue.py::test_log_expired_dry_mode_previews_the_stamp_and_writes_nothing

### Requirement: the guard check reports a log_expired row as its own shape, never red

`make pipeline-failure-guard-check` MUST report a ledger row carrying `log_expired` as its OWN
shape (a drain) and MUST NOT treat it as an in-flight fix, and MUST NOT fail it with the
closed-without-guard refusal regardless of the issue's OPEN/CLOSED state — a run whose log aged out
of retention can never yield an error class for a guard test to lock, so closing its issue is
legitimate.

#### Scenario: a log_expired row is reported as its own shape, never red

- **Given** a planted ledger entry for run 200 carrying `log_expired` and `rediagnose_attempts`,
  with an issue that is OPEN and separately one that is CLOSED
- **When** `scripts/pipeline_failure_guard_check.py` verdict runs
- **Then** it exits 0 and reports a line naming `log_expired` + `TERMINAL`; it never emits the
  `closed without a fix PR or a guard test` refusal, whatever the issue state
- **Test:** tests/test_pipeline_failure_guard.py::test_log_expired_row_is_reported_as_its_own_shape_never_red
