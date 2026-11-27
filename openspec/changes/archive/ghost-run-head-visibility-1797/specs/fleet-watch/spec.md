## ADDED Requirements

### Requirement: A never-started PR head is board-visible

The fleet monitor SHALL emit one `G:<run id>:<pr>` marker when a completed `action_required`
run on a PR carried zero jobs, and SHALL emit it with the PR number even when GitHub has cleared
the run's `pull_requests` association. The marker SHALL fire once per run, and the R marker's
existing byte shape SHALL NOT change. A run with jobs, a run with no PR identity, and a run with
no jobs read SHALL NOT produce a G marker.

#### Scenario: A zero-job action_required head on an open PR

- **Given** a completed `action_required` qa-validate run whose jobs list is empty and whose
  `pull_requests` names PR #1770
- **When** the detector diffs the snapshot
- **Then** it emits `G:<run>:1770` alongside the unchanged R marker, and a second identical tick
  emits no G marker
- **Test:** `tests/test_watch_monitor.py::test_ghost_marker_names_the_pr_and_fires_once`

#### Scenario: No job evidence or no PR identity

- **Given** a run with a job, or a zero-job run with no PR, or no jobs read at all
- **When** the detector diffs the snapshot
- **Then** no G marker is emitted and no ghost state is invented
- **Test:** `tests/test_watch_monitor.py::test_ghost_marker_needs_zero_jobs_and_a_pr`

### Requirement: The job read is bounded and uses the caller's client

The monitor SHALL read jobs only for completed `action_required` runs, capped per tick, using the
`gh` client the caller pinned; an unreadable run SHALL contribute no jobs entry and therefore no
marker. The ghost decision SHALL be the one in `scripts/ghost_run_alarm.py`, not a second
implementation.

#### Scenario: A capped, explicit job read

- **Given** two `action_required` runs and one normal run, with one jobs read failing
- **When** the job leg runs on the explicit client
- **Then** only the action_required heads are read, the failed read contributes no evidence,
  and the zero-job head is recorded
- **Test:** `tests/test_watch_monitor.py::test_fetch_ghost_jobs_reads_only_action_required_heads`

#### Scenario: The offline contract

- **Given** `watch_monitor --check` with no network
- **When** the contract runs
- **Then** `G:` is a legal marker prefix and the shared ghost verdict is still the one the
  alarm uses
- **Test:** `tests/test_watch_monitor.py::test_offline_check_mode`
