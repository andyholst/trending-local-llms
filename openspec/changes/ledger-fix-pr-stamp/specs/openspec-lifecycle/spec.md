## ADDED Requirements

### Requirement: Recording the completing PR raises the pipeline-failure ledger row

When `make openspec-record-pr ISSUE=<n> PR=<m>` runs and `data/pipeline_failures.json` carries a row whose `issue_number` names #<n> with `fix_pr: null`, the recording ALSO raises that row to `fix_pr: <m>` — keeping a guard the row already names, filling a null guard from the change's own `- **Test:**` modules — and REFUSES the whole recording (exit 2, no mutation) when the guard cannot be resolved to a module that exists under `tests/`. Rows for other issues and already-raised rows are byte-identical (rule 3b).

#### Scenario: A pipeline-failure fix records its PR and the row is raised in the same step

Given a fixture repo whose ledger row for issue #99 has `fix_pr: null` and `guard: null`, and whose change locks `tests/test_fix_x.py` via a scenario `- **Test:**` line
When `openspec_record_pr --issue 99 --pr 123` runs
Then the change is archived, the row reads `fix_pr: 123` and `guard: "tests/test_fix_x.py"`, and the other planted row is byte-identical

- **Test:** tests/test_ledger_fix_pr_stamp.py::test_record_pr_stamps_fix_pr_and_guard_from_the_change

#### Scenario: A row that already names its landed guard keeps it

Given a ledger row for issue #99 with `fix_pr: null` and `guard: "tests/pre.py"` where that module exists
When the recording runs
Then `fix_pr` is raised and the guard stays `"tests/pre.py"` — the row's own landing evidence outranks the change's Test ref

- **Test:** tests/test_ledger_fix_pr_stamp.py::test_a_row_that_already_names_its_guard_keeps_it

#### Scenario: A stamp with no resolvable guard refuses the whole recording

Given a ledger row for issue #99 with `fix_pr: null` and `guard: null` whose change names a test module that does not exist under `tests/`
When the recording runs
Then it exits 2 naming the row, the ledger bytes are untouched, and the change is NOT archived — no half-state where `fix_pr` is raised without a guard

- **Test:** tests/test_ledger_fix_pr_stamp.py::test_null_guard_with_no_resolvable_test_refuses_exit_2_and_writes_nothing

#### Scenario: An ordinary implementation issue records normally with no ledger row

Given a ledger whose only row names issue #555 while the recording is for issue #99
When the recording runs
Then it exits 0, archives the change, and the ledger bytes are untouched

- **Test:** tests/test_ledger_fix_pr_stamp.py::test_an_issue_with_no_ledger_row_records_normally

#### Scenario: An already-raised row is never rewritten

Given a ledger row for issue #99 carrying `fix_pr: 77` and `guard: "tests/pre.py"`
When a later recording runs for the same issue
Then the ledger file is byte-identical (rule 3b — a raised value is never re-stamped or shrunk)

- **Test:** tests/test_ledger_fix_pr_stamp.py::test_an_already_raised_row_is_never_rewritten

#### Scenario: The already-archived re-run still repairs a null row

Given the change for issue #99 already lives in `archive/` while its ledger row still has `fix_pr: null` (the measured #833 keeper shape)
When the recording re-runs
Then it exits 0 as a benign re-run AND raises the row with the PR's guard test

- **Test:** tests/test_ledger_fix_pr_stamp.py::test_the_rerun_after_archive_still_raises_a_null_row

#### Scenario: The stamp rides the already-wired target

Given `make openspec-record-pr` is the target issue-bot calls after `gh pr create`
When the tree is scanned
Then the Makefile defines the target, `issue-bot.yml` calls `make openspec-record-pr`, and `ARCHITECTURE.md` names the ledger raise beside the script's role (rule 6h)

- **Test:** tests/test_ledger_fix_pr_stamp.py::test_the_stamp_is_wired_where_pipeline_failures_get_fixed
