# alarms

## ADDED Requirements

### Requirement: the filer records every target as the bare parseable `make <target>`

`make pipeline-failure-issue` MUST extract failing targets through the ONE `normalize_target`
seam in `scripts/pipeline_failure_issue.py`: a log line whose bracket names the
`file:<line>: <name>` form (e.g. `make: *** [Makefile:1384: sweep-alarm]`) contributes the BARE
target `sweep-alarm`, a bare bracketed name passes through unchanged, and the two forms of one
target dedupe to the single name. Every ledger row's `targets` and every reproduction command the
filer quotes is therefore the runnable `make <target>` (rule 6m).

#### Scenario: the bracketed file:line form normalises at extraction and dedupes with the bare form

- **Given** a log block containing both `make: *** [validate] Error 1` and
  `make: *** [Makefile:1231: validate] Error 2`
- **When** `scripts/pipeline_failure_issue.py` extracts the failing targets
- **Then** `failed_make_targets` returns exactly `["validate"]` — the decorated form normalises to
  the bare target and the two forms dedupe to one name — and `normalize_target("live-smoke")`
  passes a bare name through unchanged
- **Test:** tests/test_pipeline_failure_issue.py::test_the_makefile_line_target_form_normalises_to_the_bare_target

### Requirement: a sweep converges stored warped rows and leaves a uniform ledger untouched

`make pipeline-failure-issue` MUST, once per sweep, normalise the stored ledger's row targets
through `normalize_target`: a warped row's targets become the bare parseable names, every stored
run id survives (rule 3b: no row removed, no value re-spelled beyond the decoration strip), and a
ledger whose rows are already uniform is NOT rewritten — the sweep writes no change and prints no
normalisation line.

#### Scenario: a warped stored row is normalised on the sweep and every run id survives

- **Given** a ledger holding a warped row (targets `["Makefile:1231: _implement-issue",
  "live-smoke"]`), a uniform row and a still-undiagnosed row, with the stub `gh` serving the scene
- **When** `scripts/pipeline_failure_issue.py` sweeps
- **Then** it exits 0, prints the `targets normalised on <n> row(s)` line, the warped row's
  targets become `["_implement-issue", "live-smoke"]`, the uniform row is byte-identical, and all
  three run ids are still present; a SECOND sweep on the now-uniform ledger leaves the file
  byte-identical and prints no normalisation line
- **Test:** tests/test_pipeline_failure_issue.py::test_a_sweep_normalises_stored_rows_and_leaves_a_uniform_ledger_untouched

### Requirement: a re-diagnosis raise outputs uniform targets from a warped row

When the re-diagnosis pass (issue #969) raises a still-UNDIAGNOSED ledger row, it MUST
re-normalise the row's WHOLE grown targets list — the row's pre-existing warped entries included —
so the raised row's `targets` is uniformly the bare parseable target, matching its sibling rows.

#### Scenario: raising a row whose stored targets carry the file:line form outputs bare names

- **Given** a ledger row for run 100 carrying `undiagnosed` and warped targets
  `["Makefile:1384: validate"]`, while the stub `gh` serves the run's readable log
- **When** `scripts/pipeline_failure_issue.py` sweeps
- **Then** the row is raised (a `rediagnosed_utc` is stamped) and its `targets` is exactly
  `["validate"]` — the old warped entry normalised, no duplicate of the newly extracted name
- **Test:** tests/test_pipeline_failure_issue.py::test_a_raise_renormalises_the_row_s_existing_warped_targets
