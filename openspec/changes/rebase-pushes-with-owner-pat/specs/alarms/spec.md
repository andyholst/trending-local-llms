# alarms

## ADDED Requirements

### Requirement: A main-pipeline run that concluded with ZERO jobs is a GHOST and an alarm

`make ghost-run-alarm` (`scripts/ghost_run_alarm.py`, run by `queued-alarm.yml`
with the default `github.token`, read-only) MUST flag every
`pull_request`-triggered run of a main pipeline in its window that concluded in a
bad state with zero jobs scheduled (`action_required`, `jobs_total: 0`) or
concluded `success` while having run zero jobs — the issue #1115 shape where the
pipeline never FAILED, it never RAN. A run with real jobs, a concurrency-SKIPPED
run, and a ghost outside the window are not alarms. The DECISION lives in the
script (`ghost_verdict`, rule 6d); ghosts go loud via exit 1 (the sweep goes RED
naming each ghost run); an unreadable GitHub read exits 2 rather than reporting
a pass.

#### Scenario: an action_required run with zero jobs is flagged

- **Given** a recorded `pull_request` qa-validate run that concluded
  `action_required` with `jobs_total: 0`
- **When** the real `scripts/ghost_run_alarm.py` reads it through its stub-`gh`
  fixture
- **Then** it exits 1 and names that run URL as a ghost
- **Test:** tests/test_auto_merge_rebase.py::test_ghost_alarm_flags_completed_pr_runs_with_zero_jobs

#### Scenario: a success-with-zero-jobs run is flagged and clean runs are not

- **Given** a planted mix: `success` with 0 jobs (ghost), a run with real jobs,
  and a `[skip]`-concurrency run
- **When** the real alarm runs over it
- **Then** only the zero-job `success` run is named, the skip is not, and a
  ghost-free window exits 0
- **Test:** tests/test_auto_merge_rebase.py::test_ghost_alarm_flags_completed_pr_runs_with_zero_jobs

#### Scenario: an unreadable pipeline state is a loud failure, never a silent clean

- **Given** the `gh run list` read fails
- **When** the real alarm runs
- **Then** it exits 2 naming the failed read
- **Test:** tests/test_auto_merge_rebase.py::test_ghost_alarm_flags_completed_pr_runs_with_zero_jobs
