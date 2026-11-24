## ADDED Requirements

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
