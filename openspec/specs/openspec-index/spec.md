# openspec-index Specification

## Purpose
TBD - created by archiving change openspec-index-repair. Update Purpose after archive.

## Requirements

### Requirement: a red master index gate has an event-driven keeper with a script-owned verdict

When the push-to-master `validate` goes red at `openspec-check`, qa-validate's
`index-repair` job SHALL run `make openspec-index-repair` against the exact
post-merge tree, and the verdict SHALL belong to `scripts/openspec_index_repair.py`
(rule 6d): it prints exactly one `DRIFT=none|index-only` line. Only an
`index-only` verdict may land a keeper PR, the job SHALL run only after the
`guard` and only on a FAILED push to master, and the keeper PR SHALL never merge
itself. A committed index that exists but cannot be read SHALL exit 2 naming the
refusal — never a silent clean.

#### Scenario: the exact post-merge drift classifies index-only and the rewrite is current

- **GIVEN** a committed index written while change `alpha` was ACTIVE, and a merge
  that archived `alpha` and landed a new change `beta`
- **WHEN** `--classify-and-write` runs against that tree
- **THEN** it exits 0, prints `DRIFT=index-only`, names `alpha` and `beta`, and the
  rewritten index passes `openspec_index.py --check`

- **Test:** `tests/test_openspec_index_repair.py::test_stale_index_after_a_merge_classifies_index_only_and_rewrites`

#### Scenario: a current index classifies none and writes nothing

- **GIVEN** an index that is exactly what the generator would produce
- **WHEN** `--classify-and-write` runs
- **THEN** it exits 0 printing `DRIFT=none` and the index bytes are untouched (the
  red had another cause; the workflow lands nothing)

- **Test:** `tests/test_openspec_index_repair.py::test_current_index_classifies_none_and_writes_nothing`

#### Scenario: a deleted generated file is index-only drift

- **GIVEN** a changes tree whose committed `OPENSPEC.md` is gone
- **WHEN** `--classify-and-write` runs
- **THEN** it writes the index and the verdict is `index-only`

- **Test:** `tests/test_openspec_index_repair.py::test_missing_generated_file_is_index_only_drift`

#### Scenario: an unreadable index is loud, never clean

- **GIVEN** an index file that cannot be read
- **WHEN** `--classify-and-write` runs
- **THEN** it exits 2 and names the refusal

- **Test:** `tests/test_openspec_index_repair.py::test_unreadable_index_is_loud_never_a_silent_clean`

### Requirement: the keeper lands through the Makefile and closes nothing

`scripts/openspec_index_repair.py` SHALL be reachable only through
`make openspec-index-repair` and `make openspec-index-repair-pr-body`, both called
by qa-validate (rules 6d/6m), and the composed keeper PR body SHALL carry no
closing keyword — it records drift and `refs` the tracking issue. The keeper branch
shape `ci/openspec-index-repair-<UTC>` SHALL implement no issue under the real
closure parser.

#### Scenario: the body closes none under the real parser

- **GIVEN** the composed keeper PR body and branch `ci/openspec-index-repair-20261112T120000Z`
- **WHEN** `scripts/pr_closure.py`'s `implemented_issue` and `check` run over them
- **THEN** no implemented issue is found and no problem is reported

- **Test:** `tests/test_openspec_index_repair.py::test_keeper_pr_body_implements_no_issue_and_closes_none`

#### Scenario: the wiring is one seam

- **GIVEN** the Makefile and qa-validate.yml on disk
- **WHEN** the wiring test runs
- **THEN** both targets exist, qa-validate calls both through `make`, and no step
  reaches the script directly

- **Test:** `tests/test_openspec_index_repair.py::test_the_repair_is_wired_through_make_and_qa_validate`

#### Scenario: the job contract is pinned

- **GIVEN** qa-validate.yml
- **WHEN** the job-contract test runs
- **THEN** `index-repair` needs `[guard, validate]`, lands only on a failed
  push-to-master, commits as the repo agent, holds only `contents`/`pull-requests`
  write, and contains no merge and no `pull_request` landing condition

- **Test:** `tests/test_workflows.py::test_index_repair_job_is_the_event_driven_keeper_for_a_red_master_index_gate`

### Requirement: the registry names the real keeper pathway for the index gate

`scripts/master_alarm.py`'s GATES registry SHALL name `openspec-check`'s keeper as
`qa-validate index-repair + architecture-bot` (event-driven keeper, weekly
backstop), and `tests/test_master_alarm.py` SHALL pin the gate→keeper mapping so a
new keeper gate naming an unverified pathway reds the suite.

#### Scenario: the registry and its tests agree

- **GIVEN** the GATES registry and the validate job's `make` gates derived from the
  workflow tree
- **WHEN** `test_every_validate_gate_is_on_a_list` runs
- **THEN** every gate sits on the keeper or alarm list, and each keeper name equals
  the pinned expected pathway

- **Test:** `tests/test_master_alarm.py::test_every_validate_gate_is_on_a_list`

### Requirement: a stale index names the drift it actually found

`make openspec-index-check` SHALL fail when the committed `OPENSPEC.md` differs
from what `--write` would produce, and its message SHALL name the drift it found:
changes on disk with no row, rows for changes that no longer exist, the **count
line** when its numbers drifted (quoting the number the disk needs), and the rows
whose data changed. It SHALL NOT attribute a count-line drift to the rows, and it
SHALL NOT assert a cause it did not find.

#### Scenario: a count-line drift is named as the count line

- **GIVEN** a committed index whose rows are all present and identical and whose
  only drift is the `Active changes: **N**` line (measured on `master`, run
  38865506979: the file said 30, the tree held 31)
- **WHEN** `--check` runs
- **THEN** it exits non-zero, names the count line and the number the disk needs,
  and does NOT claim the rows' data changed

- **Test:** `tests/test_openspec_index.py::test_a_stale_count_line_is_named_and_not_blamed_on_the_rows`

#### Scenario: a row whose data moved is named

- **GIVEN** a change whose `tasks.md` moved after the index was written, so its
  row's task progress no longer matches
- **WHEN** `--check` runs
- **THEN** it exits non-zero and names that change among the rows whose data changed

- **Test:** `tests/test_openspec_index.py::test_a_row_whose_data_moved_is_named`

#### Scenario: a change with no row is named

- **GIVEN** a change directory on disk that has no row in the index
- **WHEN** `--check` runs
- **THEN** it exits non-zero and lists the change as having no row

- **Test:** `tests/test_openspec_index.py::test_change_with_no_row_fails_the_check`

### Requirement: write and check agree

`--write` SHALL produce exactly the file `--check` accepts, so a regenerated index
is never stale, and this repository's committed index SHALL be current.

#### Scenario: a regenerated index passes the check

- **GIVEN** a fixture change tree with no index yet
- **WHEN** `--write` runs and then `--check` runs
- **THEN** both exit 0

- **Test:** `tests/test_openspec_index.py::test_write_then_check_is_green`

#### Scenario: the committed index is current

- **GIVEN** this repository's real `OPENSPEC.md` and `openspec/changes/`
- **WHEN** the check runs and the rows are compared with the directories
- **THEN** the check exits 0 and every change directory has a row

- **Test:** `tests/test_openspec_index.py::test_real_repo_index_is_current_and_lists_every_change`
