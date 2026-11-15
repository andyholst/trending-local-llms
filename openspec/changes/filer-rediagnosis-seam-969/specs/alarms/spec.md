# alarms

## ADDED Requirements

### Requirement: The filer re-reads every still-UNDIAGNOSED ledger row on each sweep

`make pipeline-failure-issue` MUST, on every run, re-read the log of every ledger row in
`data/pipeline_failures.json` that carries `undiagnosed` and no `rediagnosed_utc`: re-derive the
failed job from the run's own job list (by the job name the row recorded), fetch the log through
the escape-tolerant reader, and raise the row APPEND-ONLY — adding `rediagnosed_utc`, a scrubbed
`error_excerpt` and a `rediagnosis_note`, and growing `targets` with only the new `make` targets
the log names (rule 3b: no key or value removed, the `undiagnosed` field KEPT). `fix_pr` and
`guard` MUST stay untouched — attribution is each fix's own decision (rule 6r). A row whose log is
still unreadable MUST be reported loudly and MUST stay eligible for the next sweep; a readable log
with no error-shaped line MUST leave the row UNDIAGNOSED and report that, never mark it done.
`--dry` previews the raise and writes nothing.

#### Scenario: a planted UNDIAGNOSED row becomes diagnosed on the next stubbed sweep

- **Given** a ledger seeded with one row for run 100 (job `validate`) carrying `undiagnosed` and
  no `rediagnosed_utc`, while the stub `gh` serves the run's jobs and a readable log
- **When** `scripts/pipeline_failure_issue.py` sweeps
- **Then** the row gains `rediagnosed_utc`, an `error_excerpt` quoting `make: *** [validate]
  Error 1` with the planted secret masked, `targets` grown to `["validate"]`, and the original
  `undiagnosed` value remains — while NO new issue is filed
- **Test:** tests/test_pipeline_failure_issue.py::test_rediagnose_pass_raises_a_still_undiagnosed_row_from_the_readable_log

#### Scenario: a still-unreadable log leaves the row UNDIAGNOSED and says so

- **Given** the same seeded UNDIAGNOSED row and a stub `gh` whose log fetch fails twice
- **When** the sweep runs
- **Then** it exits 0, prints a loud `rediagnose run 100: log still unreadable` line, and the row
  gains NO `rediagnosed_utc` — it stays eligible for the next sweep
- **Test:** tests/test_pipeline_failure_issue.py::test_a_still_unreadable_log_leaves_the_row_undiagnosed_and_retries_next_sweep

#### Scenario: a rediagnosed row is never re-fetched, and dry mode writes nothing

- **Given** a seeded row that already carries `rediagnosed_utc` (with the log endpoint armed to
  fail), and separately a seeded UNDIAGNOSED row under `--dry`
- **When** the sweep runs in each case
- **Then** the rediagnosed row is left untouched and no re-diagnosis line is printed for it, and
  the dry sweep prints `WOULD RAISE` while leaving the ledger file unchanged
- **Test:** tests/test_pipeline_failure_issue.py::test_a_rediagnosed_row_is_never_re_fetched_and_dry_previews_without_writing
