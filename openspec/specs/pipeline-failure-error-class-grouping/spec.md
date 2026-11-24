# pipeline-failure-error-class-grouping Specification

## Purpose
TBD - created by archiving change filer-error-class-grouping-1557. Update Purpose after archive.

## Requirements

### Requirement: The master/schedule half files ONE issue per STABLE error class per window

`sweep()` in `scripts/pipeline_failure_issue.py` SHALL collect the diagnostics of every unfiled
concluded-bad run/job first, group them by the SAME stable seam the PR-blockage half uses
(`failure_shape`, with `exact_failure_shape` as the second axis), and file exactly ONE issue per
class per window. EVERY member run SHALL still append its own ledger row (append-only), carrying
the additive keys `failure_class` and `class_runs`. A class of one run SHALL file exactly as it did
before this change. No existing ledger key or value SHALL be removed or rewritten.

#### Scenario: N runs of one recurring defect file one issue and N ledger rows

- **Given** four concluded-bad push-to-master runs in one window, three of which carry the same
  failing region with only run-specific chatter differing
- **When** `make pipeline-failure-issue` sweeps the window
- **Then** exactly TWO issues are filed — one for the three-run class and one for the different
  defect — and all four run ids appear in the ledger
- **Test:** tests/test_pipeline_failure_issue.py::test_the_master_schedule_half_files_one_issue_per_error_class

#### Scenario: every member row carries the class and the whole member set

- **Given** the three-run class above
- **When** the ledger is read back
- **Then** each of the three rows names the SAME `issue_number`, the SAME non-empty `failure_class`
  and `class_runs == [200, 201, 202]`, while the other class's row names a DIFFERENT issue
- **Test:** tests/test_pipeline_failure_issue.py::test_the_master_schedule_half_files_one_issue_per_error_class

#### Scenario: the class body names the other member runs

- **Given** the three-run class is filed
- **When** its issue body is composed
- **Then** an additive sentence names the two other member run ids, and the five message-pattern
  sections stay present and in order
- **Test:** tests/test_pipeline_failure_issue.py::test_the_master_schedule_half_files_one_issue_per_error_class

#### Scenario: a dry run previews the class with its member count and writes nothing

- **Given** the same four-run window
- **When** the sweep runs with `--dry`
- **Then** stdout previews each class with its member count (`3 run(s) 200, 201, 202`) and no
  ledger file and no issue are written
- **Test:** tests/test_pipeline_failure_issue.py::test_the_error_class_dry_run_previews_without_writing

#### Scenario: a re-run over the appended ledger files nothing

- **Given** a sweep that already appended all four member rows
- **When** the same sweep runs again
- **Then** no further issue is created, because every member run id is now known
- **Test:** tests/test_pipeline_failure_issue.py::test_the_master_schedule_half_files_one_issue_per_error_class

#### Scenario: the pinning test fails on the pre-change filer

- **Given** `scripts/pipeline_failure_issue.py` from `origin/master` (one issue per run)
- **When** the two new test functions run against it
- **Then** seven checks FAIL — the class is not formed, the member clause is absent and the
  additive keys are missing — proving the guard locks the grouping and not the fixture
- **Test:** tests/test_pipeline_failure_issue.py::test_the_master_schedule_half_files_one_issue_per_error_class

### Requirement: An error class keeps ONE member per run

`group_failure_classes()` in `scripts/pipeline_failure_issue.py` SHALL collapse every class group
to at most one member per run id, keeping the earliest job of that run. `sweep()` SHALL therefore
append exactly ONE ledger row per run (never one per failed job), and the filed issue's member
sentence and `class_runs` SHALL list each run once. A class whose runs each carry one bad job SHALL
behave exactly as before this requirement.

#### Scenario: a run with six cancelled jobs files one row

- **Given** one concluded-bad push-to-master run carrying SIX cancelled jobs of the same error class
- **When** `make pipeline-failure-issue` sweeps the window
- **Then** ONE issue is filed, the ledger holds exactly ONE row for that run, `class_runs == [300]`,
  and the body claims no further member runs
- **Test:** tests/test_pipeline_failure_issue.py::test_a_run_with_several_bad_jobs_is_one_member_and_one_ledger_row

#### Scenario: the pre-existing grouping still holds

- **Given** three runs of one class plus one run of a different class
- **When** the sweep runs
- **Then** two issues are filed, every run appends its own row and the three-run class body names the
  other two runs — unchanged from #1557
- **Test:** tests/test_pipeline_failure_issue.py::test_the_master_schedule_half_files_one_issue_per_error_class

#### Scenario: the pinning test fails on the pre-#1615 filer

- **Given** `scripts/pipeline_failure_issue.py` from `origin/master` (grouping without the collapse)
- **When** the new test function runs against it
- **Then** four checks FAIL and the captured row shows `class_runs == [300, 300, 300, 300, 300, 300]`
  — proving the guard locks the collapse and not the fixture
- **Test:** tests/test_pipeline_failure_issue.py::test_a_run_with_several_bad_jobs_is_one_member_and_one_ledger_row
