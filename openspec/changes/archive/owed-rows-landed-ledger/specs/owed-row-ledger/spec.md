# owed-row-ledger

## ADDED Requirements

### Requirement: The owed-row marker has ONE registered name and shape

`scripts/bot_markers.py` MUST define the owed-row ledger marker's name, shape, and parser
(rule 6j: marker names and shapes live in exactly one place). The marker names the AGENTS.md
section it is owed to and the exact needle the landed row must carry. Any reader or writer in
the tree MUST go through that module rather than re-spelling the marker.

#### Scenario: a well-formed marker parses through the shared helper

- **Given** a body containing `<!-- owed-row: section=8 needle=tests/test_refresh_base.py -->`
- **When** the shared parser reads it
- **Then** it returns the section anchor `8` and the needle `tests/test_refresh_base.py`
- **Test:** tests/test_owed_rows.py::test_the_owed_row_marker_is_registered_and_parses

#### Scenario: a malformed marker is loud, never silent

- **Given** a body containing an `owed-row` marker missing `needle=` or carrying an unquoted
  space-containing needle without quotes
- **When** the ledger check reads that issue
- **Then** the report names the issue and the malformed marker and the check exits 2
- **Test:** tests/test_owed_rows.py::test_a_malformed_owed_row_marker_is_loud

### Requirement: `make owed-rows-check` reports every open owed row as landed or outstanding

The check MUST read the open queue issues through the ONE queue reader (`scripts/issue_queue.py`),
parse owed-row markers from each whole thread, search `AGENTS.md`, and print one line per owed row
as `landed` with the `AGENTS.md:<line>` evidence or `outstanding` with the expected section — so
an issue whose row already exists is closable on evidence, not on re-reading a thread. A check
that finds no markers in an issue that carries none reports it as `no marker`, never as landed.

#### Scenario: a landed row is reported with its evidence line

- **Given** a fixture where an open queue issue's thread carries an owed-row marker whose needle
  appears in AGENTS.md §8
- **When** the real check script runs against the fixture (stub `gh` on PATH)
- **Then** the report names the issue, the row, `landed`, and the matching AGENTS.md line
- **Test:** tests/test_owed_rows.py::test_a_landed_owed_row_is_reported_with_evidence

#### Scenario: an outstanding row is reported as outstanding

- **Given** a fixture where the needle appears nowhere in AGENTS.md
- **When** the real check script runs against the fixture
- **Then** the report names the issue, the row, and `outstanding`
- **Test:** tests/test_owed_rows.py::test_an_outstanding_owed_row_is_reported

#### Scenario: the backlog issues of #523 are in the ledger

- **Given** the live repository after this change
- **When** `make owed-rows-check REPO=andyholst/trending-local-llms` runs
- **Then** the #523 backlog (#212 #314 #322 #324 #380 #385 #405 and the #503-folded rows) each
  appear with a parsed marker, and rows already present in AGENTS.md report `landed` with their
  evidence lines
- **Test:** verified by a live `make owed-rows-check` run recorded on the PR (no offline fixture
  can assert live GitHub state)

### Requirement: the ledger target is wired through the Makefile and a pipeline

`make owed-rows-check` MUST be the only entry point to the script (rule 6m), host-side like the
other gh-bound verifiers, and MUST be called by the `queued-alarm` pipeline's alarm job — a
scheduled weekly read of live repo state, never a PR gate that could red an unrelated PR. The
exit contract is: 0 = report produced (landed or outstanding), 2 = the ledger could not be read.

#### Scenario: a workflow calls the target

- **Given** `.github/workflows/queued-alarm.yml`
- **When** the pipeline's alarm job runs
- **Then** it calls `make owed-rows-check REPO=...` as its own step
- **Test:** tests/test_owed_rows.py::test_the_pipeline_calls_the_ledger_target

#### Scenario: no test patches the product

- **Given** the test module drives the real script with a stub `gh` and recorded fixtures
- **When** `tests/test_makefile_only.py` scans it
- **Then** it finds no patched, rebound or faked `scripts/` symbol
- **Test:** tests/test_makefile_only.py::test_no_test_fakes_a_product_symbol (existing guard)
