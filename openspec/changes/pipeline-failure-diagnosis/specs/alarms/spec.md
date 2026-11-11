# alarms

## ADDED Requirements

### Requirement: A red main pipeline run is diagnosed as an issue carrying its log's error block

`make pipeline-failure-issue` MUST file one `tech-debt` issue per failing job of every
main-pipeline run (qa-validate, refresh-bot, issue-bot, issue-review-bot, architecture-bot,
queued-alarm) that concluded in failure or cancellation on a `push` to master or a `schedule`
within its window; the body MUST follow the message pattern (issue #771), carry the registered
`pipeline-run-failure` run-id marker, the bounded deduplicated error block from the job log, and
a `make <target>` reproduction read from the log itself. The error block MUST be scrubbed
through `scripts/scrub_log.py`'s redactor before it is written, and a log that cannot be read
files the issue UNDIAGNOSED rather than skipping it.

#### Scenario: every concluded-bad in-window run files one diagnosed issue

- **Given** a stub `gh` returning a push-to-master failure, a scheduled cancellation, a success, a
  manual dispatch, and an out-of-window failure for qa-validate.yml
- **When** `scripts/pipeline_failure_issue.py` sweeps the main pipelines
- **Then** exactly two issues are filed, each carrying the run-id marker, the five pattern
  sections in order, the log's error block (deduped) and the make target the log names
- **Test:** tests/test_pipeline_failure_issue.py::test_filing_diagnoses_every_failure_with_the_log_error_block

#### Scenario: a secret in the job log never reaches the issue body

- **Given** a job log containing a live credential value in a Bearer line, and the credential's
  variable name set in the environment
- **When** the filer composes the issue body
- **Then** the value appears in NO spelling in the body and the masked form does
- **Test:** tests/test_pipeline_failure_issue.py::test_filing_diagnoses_every_failure_with_the_log_error_block

#### Scenario: an unreadable log files an undiagnosed issue, loudly

- **Given** a failure whose job-log fetch is refused
- **When** the filer composes the issue
- **Then** the issue is filed, its body says the log could not be read, and the ledger records the
  entry as undiagnosed
- **Test:** tests/test_pipeline_failure_issue.py::test_undiagnosed_filing_is_loud_never_a_skip

#### Scenario: a failed pipeline-state read exits 2 and files nothing

- **Given** a sweep whose run-list read is refused
- **When** the filer finishes
- **Then** the process exits 2 naming READ FAILED, no issue is filed, and no ledger is written
- **Test:** tests/test_pipeline_failure_issue.py::test_read_failures_exit_2_never_a_fake_clean

### Requirement: The failure ledger is append-only and dedups against both memories

`data/pipeline_failures.json` MUST record every diagnosed run exactly once. The filer MUST skip a
run already in the ledger OR already named by a `pipeline-run-failure` marker on any issue
(open or closed), and a sweep that appends MUST land its append as a ledger PR whose body
references the filed issues and closes none (rule 6e).

#### Scenario: a filed run is never filed twice

- **Given** two sweeps over the same failing runs
- **When** the second sweep reads the ledger written by the first
- **Then** it files nothing new
- **Test:** tests/test_pipeline_failure_issue.py::test_ledger_and_marker_dedup_file_one_run_once_ever

#### Scenario: a closed fixed failure is not re-filed by a later sweep

- **Given** a failing run whose failure was already filed and CLOSED via a marker issue, with a
  fresh ledger
- **When** the sweep reads issues with `--state all`
- **Then** the run files nothing and still lands in the ledger as marker-matched
- **Test:** tests/test_pipeline_failure_issue.py::test_ledger_and_marker_dedup_file_one_run_once_ever

#### Scenario: the ledger PR body records issues and closes none

- **Given** a ledger with recorded runs
- **When** `make pipeline-failure-ledger-pr-body` composes the body
- **Then** it tables the runs with `refs #<issue>` and contains no closing keyword
- **Test:** tests/test_pipeline_failure_issue.py::test_ledger_pr_body_is_generated_and_carries_no_closing_keyword

### Requirement: A diagnosed pipeline failure may not close without its regression guard

`make pipeline-failure-guard-check` MUST run in qa-validate's `validate` job and exit 1 when a
ledger entry's issue is CLOSED while the entry names no fix PR and no guard test, when a fix PR's
`guard` is not a collected `tests/test_*.py` on disk, or when a CLOSED marker issue is recorded by
no ledger entry. An open fix in flight is reported, never red; a missing or corrupt ledger exits
2 rather than reporting a clean scan.

#### Scenario: closed-without-guard is red in every shape

- **Given** planted ledgers: a CLOSED issue with no fix PR or guard; a fix PR naming a guard file
  that does not exist; a fix PR naming no guard at all
- **When** `scripts/pipeline_failure_guard_check.py` judges each
- **Then** each is exit 1 naming the missing fix PR or guard test
- **Test:** tests/test_pipeline_failure_guard.py::test_closed_without_guard_is_red

#### Scenario: the measured guarded close is green

- **Given** the committed ledger row (run 43088760321, issue #800, fix PR #808, guard
  `tests/test_openspec_archive_check.py`)
- **When** the gate reads the real ledger
- **Then** it exits 0 and counts the guarded close
- **Test:** tests/test_pipeline_failure_guard.py::test_closed_with_landed_fix_and_guard_is_green

#### Scenario: an in-flight or indeterminate fix is reported, never red

- **Given** planted ledgers with an OPEN marker issue, an issue whose state cannot be read, and an
  undiagnosed pending entry
- **When** the gate judges them
- **Then** it exits 0 with a report line per entry
- **Test:** tests/test_pipeline_failure_guard.py::test_fix_in_flight_is_reported_never_red

#### Scenario: a closed marker issue the ledger never recorded is red

- **Given** a CLOSED marker issue whose run id appears in no ledger entry
- **When** the gate compares the issue scan to the ledger
- **Then** it exits 1 naming the missing append
- **Test:** tests/test_pipeline_failure_guard.py::test_closed_marker_issue_the_ledger_never_recorded_is_red

#### Scenario: an unreadable ledger never reports clean

- **Given** a missing ledger file, a non-JSON ledger, and a malformed-shape ledger
- **When** the gate runs end to end on each
- **Then** each exits 2 naming the ledger problem
- **Test:** tests/test_pipeline_failure_guard.py::test_unreadable_ledger_exits_2_end_to_end

### Requirement: The chain is wired through the Makefile and named in the rulebook

`queued-alarm.yml` MUST run `make pipeline-failure-issue` after its alarms and land a ledger
append as a PR through the Makefile; `qa-validate.yml` MUST run `make pipeline-failure-guard-check`
as a step of the `validate` job; the filer's marker MUST be registered in
`scripts/bot_markers.py`; and `AGENTS.md` MUST carry rule 6r and its §8 guard rows.

#### Scenario: the wiring is one implementation, checked by the suites

- **Given** the Makefile, `queued-alarm.yml`, `qa-validate.yml`, `scripts/bot_markers.py`,
  `scripts/master_alarm.py` and `AGENTS.md`
- **When** either wiring test reads them
- **Then** the targets exist, the workflows call only make targets, the marker and gate are
  registered, and the rulebook rows are present
- **Test:** tests/test_pipeline_failure_issue.py::test_wiring_rulebook_and_registry
