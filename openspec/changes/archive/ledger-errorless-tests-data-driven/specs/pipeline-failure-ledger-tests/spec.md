## ADDED Requirements

### Requirement: Shipped-ledger assertions derive expectations from row data, not a frozen snapshot

The two "shipped ledger" tests for the pipeline-failure ledger SHALL compute their expected
errorless/attributed/pending sets independently from the ledger's row dicts — using the two keys
the re-diagnosis raise writes (`error_excerpt` / `rediagnosed_excerpt`) — and assert the real
seam's output against those derived values. They SHALL NOT hard-code a frozen count of errorless
rows, a frozen "N diagnosed / M attributed" summary, or a frozen set of run ids. This keeps the
#1136 invariant checkable after the sweep's re-diagnosis pass legitimately diagnoses the rows and
the keeper ledger PR lands that append (rule 3b), instead of going red the moment the pipeline
does what #1136 asks.

#### Scenario: The gate reports every errorless fix-claimed row regardless of count

- **Given** the real shipped ledger with some fix-claimed rows carrying an error block and some
  carrying none under either spelling
- **When** `G.verdict` runs over that ledger with the stamped rows' states
- **Then** the report names exactly the errorless fix-claimed runs with "NO error block", and the
  summary's "diagnosed failure(s)" / "attributed without a diagnosis" counts equal the counts
  derived from the row dicts, whether that count is five, zero, or another value
- **Test:** tests/test_pipeline_failure_guard.py::test_the_committed_ledger_classifies_its_errorless_rows

#### Scenario: The re-diagnosis selector returns exactly the errorless, unraised rows

- **Given** the real shipped ledger after a re-diagnosis pass has raised `error_excerpt` into the
  previously-errorless rows
- **When** `F.rediagnose_pending` selects rows to fetch
- **Then** the selected set equals the rows with no error block under either spelling, no
  `rediagnosed_utc`, and no `log_expired` — computed independently of the selector — so an empty
  pending set after a completed pass is correct, not a failure
- **Test:** tests/test_pipeline_failure_issue.py::test_the_committed_ledger_s_errorless_rows_are_exactly_the_pending_set
