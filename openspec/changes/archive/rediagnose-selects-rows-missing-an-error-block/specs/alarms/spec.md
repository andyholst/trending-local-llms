# alarms

## ADDED Requirements

### Requirement: The re-diagnosis pass selects a ledger row by the absence of a diagnosis

`make pipeline-failure-issue` MUST decide which ledger rows still need a diagnosis from the
diagnosis itself, through ONE predicate (`scripts/pipeline_failure_issue.py::row_is_diagnosed`):
a row is diagnosed when it carries a stored error block (`error_excerpt`, or the legacy
`rediagnosed_excerpt` spelling). The pending re-diagnosis set MUST therefore be every row that is
NOT diagnosed, has no `rediagnosed_utc`, and is not the terminal `log_expired` drain — never a set
selected by the presence of an `undiagnosed` KEY, because the filer stores `undiagnosed: None` for
a log read that SUCCEEDED and a row stamped by a ledger PR never carries the key at all. A row that
claims a landed fix (`fix_pr` + `guard`) while carrying no error block MUST be selected, fetched
and raised like any other pending row. `--dry` previews the raise and writes nothing.

#### Scenario: a stamped row with no error block is pending and gets diagnosed

- **Given** a ledger seeded with (a) a diagnosed row that cites a `pipeline-run-failure` marker,
  (b) a row already raised (`rediagnosed_utc` + `error_excerpt`, no `undiagnosed` key), and (c) a
  stamped row naming `fix_pr` + `guard` + `stamp_utc` with NO `error_excerpt`, NO `undiagnosed`,
  NO `rediagnosed_excerpt` and NO `log_expired`, while the stub `gh` serves the stamped run's jobs
  and a readable log
- **When** `scripts/pipeline_failure_issue.py` sweeps
- **Then** the pending set is exactly the stamped row (the test also spells the old marker-key
  filter and proves it selected NOTHING), the sweep prints `REDIAGNOSED run <id>`, the row gains
  `rediagnosed_utc` plus a scrubbed `error_excerpt` and grown `targets`, and its `fix_pr`, `guard`,
  `stamp_utc`, `stamp_note` and its null `undiagnosed` key all remain (rule 3b)
- **Test:** tests/test_pipeline_failure_issue.py::test_a_stamped_row_with_no_error_block_is_pending_and_gets_diagnosed

#### Scenario: a row that already carries its diagnosis is never re-fetched

- **Given** the same seeded ledger, in which rows (a) and (b) already name their diagnosis
- **When** the sweep runs, and then runs a SECOND time
- **Then** those two rows are byte-identical to what was seeded, the second sweep prints no
  `REDIAGNOSED` line, and the ledger file is unchanged by it — a diagnosed row is never
  self-annotated a second time
- **Test:** tests/test_pipeline_failure_issue.py::test_a_stamped_row_with_no_error_block_is_pending_and_gets_diagnosed

#### Scenario: the shipped ledger's errorless rows are exactly the pending set

- **Given** the committed `data/pipeline_failures.json` (20 rows)
- **When** `rediagnose_pending` is asked which rows still need a diagnosis
- **Then** the answer is exactly the five measured rows `43147240875`, `43716345030`,
  `43716362366`, `43718826142`, `43725338063` (issues #1039–#1043), every other errorless row is
  the terminal `log_expired` drain, and every row that names a `fix_pr` is diagnosed except those
  five — no row that still owes a diagnosis is invisible to the sweep
- **Test:** tests/test_pipeline_failure_issue.py::test_the_committed_ledger_s_errorless_rows_are_exactly_the_pending_set

### Requirement: A filed ledger row records the diagnosis it extracted

When `make pipeline-failure-issue` files an issue for a failing job, the ledger row it appends MUST
record the SAME scrubbed error block it posted on the issue (`error_excerpt`), so a row the filer
successfully diagnosed is never again selectable as pending; when the log read FAILED, the row MUST
name no error block, which is exactly what keeps it pending for the next sweep (issue #986). A
secret value in the block MUST be redacted by `scripts/scrub_log.py` before the ledger write,
because `data/pipeline_failures.json` is a tracked file (rule 3d).

#### Scenario: a filed row carries its own scrubbed diagnosis

- **Given** a stub `gh` serving one failing job whose log names `make: *** [sweep-alarm] Error 2`
  and a planted FAKE credential
- **When** the filer files the issue and appends its ledger row
- **Then** the row names an `error_excerpt` quoting the error line with the planted secret masked,
  and the sweep's re-diagnosis pass selects NO row for it (a diagnosed filing is never re-fetched or
  self-annotated)
- **Test:** tests/test_pipeline_failure_issue.py::test_filing_diagnoses_every_failure_with_the_log_error_block

#### Scenario: an UNDIAGNOSED filing names no error block and stays pending

- **Given** a failing job whose log cannot be read after the escape-tolerant retry
- **When** the filer files the issue UNDIAGNOSED, loudly
- **Then** the ledger row carries `undiagnosed` with NO `error_excerpt`, and `rediagnose_pending`
  selects that row for the next sweep
- **Test:** tests/test_pipeline_failure_issue.py::test_undiagnosed_filing_is_loud_never_a_skip

### Requirement: The ledger gate names a diagnosed attribution apart from an attribution with no diagnosis

`make pipeline-failure-guard-check` MUST classify a ledger row that names a landed `fix_pr` and a
collected `guard` test by whether the row ALSO carries its diagnosis. A row with no error block is
its OWN reported shape — naming the fix PR, the guard, the fact that the claimed failure cannot be
named from the ledger, and the seam that recovers it (`rediagnose_pending`) — and MUST NOT be the
closed-without-guard refusal, and MUST NOT be red: the gate's red stays reserved for a diagnosed
pipeline failure that closed with no fix PR or no guard test (issue #802). Its summary MUST report
the two counts separately (`diagnosed_attributed`, `attributed_without_diagnosis`). A stamped row
whose named guard no longer exists MUST still be red.

#### Scenario: a stamped row with no error block is its own report, never red

- **Given** a planted ledger with one CLOSED row naming `fix_pr` + `guard` (a real collected
  `tests/test_*.py`) and no `error_excerpt`
- **When** `scripts/pipeline_failure_guard_check.py.verdict` decides
- **Then** it exits 0, prints a line carrying the run id, the fix PR, the guard, `NO error block`
  and `rediagnose_pending`, and prints no `closed without a fix PR or a guard test` refusal
- **Test:** tests/test_pipeline_failure_guard.py::test_a_stamped_row_with_no_error_block_is_its_own_report_never_red

#### Scenario: the committed ledger is classified as the two classes

- **Given** the committed `data/pipeline_failures.json` and the live marker issue states
- **When** the REAL gate runs over it
- **Then** it exits 0, its summary counts 12 diagnosed+attributed rows and 5 attributed-without-a-
  diagnosis rows separately, the five errorless rows (`43147240875`, `43716345030`, `43716362366`,
  `43718826142`, `43725338063`) are each named in their own line, and the old flattened claim
  ("17 closed with a landed fix PR + guard test") is gone
- **Test:** tests/test_pipeline_failure_guard.py::test_the_committed_ledger_classifies_its_five_errorless_rows

#### Scenario: an attribution claim on a row with no diagnosis is still refused

- **Given** a ledger row stamped with `fix_pr` + `guard` that carries no error block
- **When** `make pipeline-failure-attribute --run <id> --pr <n> --guard <module> --evidence <text>`
  is asked to attribute it
- **Then** it exits 2 naming `rediagnose_pending` as the seam that owns the row, and it writes
  nothing to the ledger and posts no comment
- **Test:** tests/test_pipeline_failure_attribution.py::test_a_stamped_row_with_no_error_block_refuses_an_attribution_claim
