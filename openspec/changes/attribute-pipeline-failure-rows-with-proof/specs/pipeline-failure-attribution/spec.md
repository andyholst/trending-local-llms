## ADDED Requirements

### Requirement: A pipeline-failure ledger row is attributed only with mechanical proof

`make pipeline-failure-attribute` SHALL raise `fix_pr`, `fix_pr_merged_utc`, `attributed_utc` and
`attribution_note` (and `guard` only when the row names none already) onto a diagnosed row of
`data/pipeline_failures.json` from an attestation, and SHALL refuse (exit 2, writing nothing) when
any part of the proof fails: the named fix PR is not `merged` when read through the real `gh`
client; the named guard is not a module `make test` collects per the ONE `guard_test_exists` seam
in `scripts/pipeline_failure_guard_check.py`; the attestation's `EVIDENCE:` block names nothing
checkable per the ONE `evidence_is_checkable` gate in `scripts/issue_verdict.py`; or the row is not
diagnosed (no `error_excerpt`, or its log is `log_expired`). A refusal SHALL name the failed
condition and the run id.

#### Scenario: A proven attestation stamps the row

- **Given** a planted ledger whose row for run `99999` is diagnosed (`error_excerpt`, no
  `log_expired`), names no `fix_pr`, and a recorded `gh` fixture in which PR `1234` is `merged`
  with a merge SHA and a `tests/` file in its diff
- **When** `make pipeline-failure-attribute RUN=99999 FIX_PR=1234 GUARD=tests/test_planted.py::test_class EVIDENCE=<a real path:line>` runs
- **Then** the ledger row carries `fix_pr: 1234`, `fix_pr_merged_utc`, `guard`, `attributed_utc` and
  `attribution_note`, the exit is 0, and the printed line names the run, the PR and the guard
- **Test:** tests/test_pipeline_failure_attribute.py::test_a_proven_attestation_stamps_the_row

#### Scenario: An unmerged fix PR is refused and nothing is written

- **Given** a diagnosed unattributed row and a recorded `gh` fixture in which the named PR is
  `open` (never merged)
- **When** the seam is asked to attribute that row
- **Then** the exit is 2, the ledger is byte-identical to its input, and the refusal names the run
  and the fact that the PR is not merged
- **Test:** tests/test_pipeline_failure_attribute.py::test_an_unmerged_fix_pr_is_refused_and_nothing_is_written

#### Scenario: A guard the suite does not collect is refused

- **Given** a merged fix PR and a `GUARD=` naming `tests/test_missing.py::test_x` (no such module)
  or a path outside `tests/`
- **When** the seam is asked to attribute the row
- **Then** the exit is 2, nothing is written, and the refusal says the guard is not a module
  `make test` collects
- **Test:** tests/test_pipeline_failure_attribute.py::test_a_guard_the_suite_does_not_collect_is_refused

#### Scenario: An EVIDENCE block naming nothing checkable is refused

- **Given** a merged fix PR and a collected guard, but an `EVIDENCE:` of prose that names no
  `path:line`, no checkable path and no `make`/`python3`/`gh` command
- **When** the seam is asked to attribute the row
- **Then** the exit is 2, nothing is written, and the refusal names the evidence gate it failed
- **Test:** tests/test_pipeline_failure_attribute.py::test_an_evidence_block_naming_nothing_checkable_is_refused

#### Scenario: A row without a diagnosis cannot be attributed

- **Given** a planted ledger holding (a) a row still `undiagnosed` with no `error_excerpt` and
  (b) a row whose log is gone (`log_expired`)
- **When** the seam is asked to attribute either
- **Then** each is refused (exit 2) naming the missing diagnosis, and no invented `fix_pr` is
  written onto either
- **Test:** tests/test_pipeline_failure_attribute.py::test_a_row_without_a_diagnosis_cannot_be_attributed

### Requirement: Attribution is additive and never rewrites a recorded attribution

The seam SHALL only ADD keys to a row: an existing `guard` SHALL be kept and reported as kept, a row
that already names a `fix_pr` SHALL NOT be re-pointed at another PR, and every existing field
(`undiagnosed`, `rediagnosed_utc`, `error_excerpt`, `targets`) SHALL survive byte-identical
(rule 3b).

#### Scenario: A recorded guard is kept

- **Given** a diagnosed row that already carries `guard: "tests/test_recorded.py"` and no `fix_pr`
- **When** an attestation naming a different guard is applied
- **Then** the row keeps `tests/test_recorded.py`, gains `fix_pr`, and the output says the recorded
  guard was kept
- **Test:** tests/test_pipeline_failure_attribute.py::test_a_recorded_guard_is_kept_and_reported

#### Scenario: An attributed row is never re-pointed

- **Given** a row that already names `fix_pr: 999`
- **When** an attestation naming `FIX_PR=1234` is applied to the same run
- **Then** the exit is non-zero (or the row is reported as already attributed) and `fix_pr` is still
  `999` on disk
- **Test:** tests/test_pipeline_failure_attribute.py::test_an_attributed_row_is_never_repointed

### Requirement: The unattributed tail of the ledger is reported on the sweep

`make pipeline-failure-attribute` in report mode SHALL print every diagnosed row that names no
`fix_pr` — its run id, issue number, workflow/job, `targets` and why the landed merged-PR stamp
cannot reach it (the issue is open, or held by a verdict label) — SHALL write nothing, and SHALL
exit 0, so an unattributed row is visible on every `queued-alarm` sweep instead of waiting for a
closing PR that never arrives.

#### Scenario: Report mode names every unattributed diagnosed row

- **Given** a planted ledger holding attributed rows, unattributed diagnosed rows and a
  `log_expired` row, plus recorded issue states (one open, one closed with a verdict hold)
- **When** the seam runs in report mode
- **Then** each unattributed diagnosed row is printed with its run, issue and targets, the
  `log_expired` row is named as a drain rather than a live failure, and the ledger on disk is
  byte-identical
- **Test:** tests/test_pipeline_failure_attribute.py::test_report_mode_names_every_unattributed_row_and_writes_nothing

### Requirement: The attribution seam is wired into the pipeline that lands the ledger

`make pipeline-failure-attribute` SHALL be the only way to reach
`scripts/pipeline_failure_attribute.py` (rule 6m), and `.github/workflows/queued-alarm.yml` SHALL
call it — report mode on every sweep, stamp mode only from owner-supplied dispatch inputs — BEFORE
the step that lands a changed ledger through the existing ledger PR, so a stamped row rides the
same reviewed landing as a new diagnosis (rules 6d/6m).

#### Scenario: The sweep runs attribution before the ledger landing

- **Given** `.github/workflows/queued-alarm.yml` as checked out in this repo
- **When** the workflow's steps are read in order
- **Then** a step calls `make pipeline-failure-attribute` and that step appears before the
  ledger-PR landing step, and no step reaches `scripts/pipeline_failure_attribute.py` without
  `make`
- **Test:** tests/test_workflows.py::test_the_attribution_step_runs_before_the_ledger_landing_step

#### Scenario: A workflow that drops the attribution step is red

- **Given** a copy of `queued-alarm.yml` with the attribution step removed
- **When** the wiring test runs against that copy
- **Then** it fails, naming the missing `make pipeline-failure-attribute` call
- **Test:** tests/test_workflows.py::test_a_workflow_that_drops_the_attribution_step_is_red
