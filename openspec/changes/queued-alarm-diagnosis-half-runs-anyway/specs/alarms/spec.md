# alarms

## ADDED Requirements

### Requirement: Every detector of the queued-alarm job runs whatever a sibling detector decided

Each step of `queued-alarm.yml`'s `alarm` job that runs a `make` alarm or diagnosis target MUST
carry `if: ${{ !cancelled() }}`, so a sibling step's failure (or a runner cancellation) can never
skip a detector: a red detector is a signal, not a circuit breaker (rule 6r — the failure filer,
the ledger landing, the owed-row report and the branch-protection guard must all report even when
one alarm in the same job is red). The job itself still concludes red because a failed step keeps
its own conclusion, and the `guard` job still gates the whole `alarm` job through `needs:`.

#### Scenario: a red sweep-alarm step does not skip the failure filer

- **Given** the `alarm` job of `queued-alarm.yml` — measured run 43698769068 had step 4
  (`make sweep-alarm`) exit 2 and steps 5–10, including `make pipeline-failure-issue`, SKIPPED
- **When** the workflow text is checked for unguarded `run: make` steps in the `alarm` job
- **Then** the check finds none — every detector step after the guard carries
  `if: ${{ !cancelled() }}` — and the same check flags every one of those steps on a planted copy
  with the `if:` lines removed, so the pin fails against the pre-change shape
- **Test:** tests/test_queued_run_alarm.py::test_every_alarm_step_runs_whatever_a_sibling_decided

#### Scenario: the guard job still gates the whole alarm job

- **Given** the `alarm` job declares `needs:` on the `guard` job
- **When** the guard refuses a stranger's dispatch
- **Then** the `alarm` job is skipped whole (a step-level `if:` never bypasses a refused `guard`),
  and this change adds no step condition to the guard job itself
- **Test:** tests/test_queued_run_alarm.py::test_every_alarm_step_runs_whatever_a_sibling_decided
