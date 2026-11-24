## ADDED Requirements

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
