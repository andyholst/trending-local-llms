## ADDED Requirements

### Requirement: The `R:` marker keeps its PR identity after the PR merges

`watch_monitor.marker_state` SHALL record a run's PR number in the caller-owned state's `run_prs`
map the first time the run is seen with a non-empty `pull_requests`, and SHALL reuse that recorded
number on a later tick whose `pull_requests` is empty. GitHub clears a run's `pull_requests` once
its PR merges and the branch is deleted, so deriving the field from the live row alone loses the
thread a woken lane must read. The marker's SHAPE SHALL NOT change: a push-triggered run (no
recorded PR) keeps the shorter `R:<run>:<status>:<conclusion>[:<workflow>]` form, and a PR run
keeps its trailing `:<pr>`.

#### Scenario: A run seen while its PR is open records the PR

- **Given** a run row `{"id": 45085274450, "status": "in_progress", "name": "qa-validate", "pull_requests": [{"number": 1350}]}`
- **When** `marker_state` diffs it into an empty state
- **Then** the next state's `run_prs` maps `"45085274450"` to `"1350"`
- **Test:** tests/test_watch_monitor.py::test_r_marker_keeps_its_pr_after_the_merge_clears_the_association

#### Scenario: A post-merge tick with a cleared association still emits the PR field

- **Given** the recorded state from the previous scenario and a later row for the same run with `status: "completed"`, `conclusion: "failure"`, `pull_requests: []`
- **When** `marker_state` diffs it
- **Then** the emitted marker is `R:45085274450:completed:failure:qa-validate:1350` and `run_prs` still maps the run to `1350`
- **Test:** tests/test_watch_monitor.py::test_r_marker_keeps_its_pr_after_the_merge_clears_the_association

#### Scenario: A push run keeps the shorter shape and is not written to the map

- **Given** a run row with no `pull_requests` and no recorded PR
- **When** `marker_state` diffs it
- **Then** the marker carries no `:<pr>` field and the run id is absent from `run_prs`
- **Test:** tests/test_watch_monitor.py::test_r_marker_keeps_its_pr_after_the_merge_clears_the_association

### Requirement: The guard fails on the pre-change seam

The new scenario SHALL be RED against the base revision's `scripts/watch_monitor.py`, because the
base seam has no `run_prs` map and therefore drops the PR field on the post-merge tick. A guard
that passes on both revisions locks nothing.

#### Scenario: The base seam cannot carry the PR past the merge

- **Given** `git show origin/master:scripts/watch_monitor.py` swapped into the tree
- **When** `tests/test_watch_monitor.py` runs
- **Then** the recorded-PR and post-merge-marker checks FAIL, and they pass again once the change is restored
- **Test:** tests/test_watch_monitor.py::test_r_marker_keeps_its_pr_after_the_merge_clears_the_association
