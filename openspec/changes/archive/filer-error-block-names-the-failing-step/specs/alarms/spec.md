## MODIFIED Requirements

### Requirement: The filer quotes the failing step's own error text, not whatever filled the cap

`make pipeline-failure-issue` SHALL extract its error block from the log REGION that carries
GitHub's own `##[error]` decoration — the step that ended the job — and SHALL fill the
`MAX_ERROR_LINES` budget in this priority: error-shaped lines inside that region, then error-shaped
lines elsewhere, and only for spare room the soft `FAIL`/`FAILED` chatter emitted by a step that
concluded successfully. It SHALL name the failing step from TWO real sources — GitHub's job
`steps[]` whose conclusion is bad, and the `##[group]` label of the region the block came from —
in the filed issue body and in the ledger row (additive keys `failing_steps` and `error_region`),
and when a block yields no `make` target while the failing step is known it SHALL say so instead of
quoting chatter. Every line it quotes SHALL stay in log order, de-duplicated and capped, and any
chatter dropped for room SHALL be reported as dropped. The re-diagnosis pass SHALL extract through
the SAME seam.

#### Scenario: a passing module's FAIL chatter cannot crowd out the refusal that ended the job

- **Given** a planted job log shaped like the measured tail of qa-validate run 43725338063 — 43
  planted `FAIL:`/`PASSED … | FAILED 0` lines from steps that succeeded, then the region
  `Run make openspec-check` carrying `[openspec-index] FAIL OPENSPEC.md is stale or missing`,
  `make: *** [Makefile:367: openspec-index-check] Error 1` and `##[error]Process completed with
  exit code 2.`
- **When** the real filer extracts that log
- **Then** the block contains the `make: *** [Makefile:367: openspec-index-check]` line and the
  `[openspec-index] FAIL` line, `failed_make_targets` answers `openspec-index-check`, and the block
  is at most `MAX_ERROR_LINES` long
- **Test:** tests/test_pipeline_failure_error_block.py::test_a_passing_module_s_chatter_cannot_crowd_out_the_refusal_that_ended_the_job

#### Scenario: the block names the region it was taken from and the step GitHub names

- **Given** the same planted log together with the job's own `steps[]` list (one step
  `conclusion: failure`, later steps `skipped`)
- **When** the seam runs
- **Then** the named region is `Run make openspec-check`, `failing_step_names` answers exactly the
  step GitHub marked bad, and both appear in the filed body
- **Test:** tests/test_pipeline_failure_error_block.py::test_the_failing_step_is_named_from_github_s_own_steps_and_the_log_region

#### Scenario: dropped chatter is reported, never silently swallowed

- **Given** a planted log whose succeeded regions hold more soft `FAIL:` lines than the cap and
  whose failing region holds the refusal
- **When** the seam extracts it
- **Then** every failing-region line survives, the soft chatter from succeeded regions is dropped,
  and the block ends with a line naming how many lines were dropped and why
- **Test:** tests/test_pipeline_failure_error_block.py::test_chatter_dropped_for_room_is_announced_in_the_block

#### Scenario: an ungrouped log still yields a diagnosis

- **Given** a log containing no `##[group]` marker at all (a job log GitHub truncated)
- **When** the seam extracts it
- **Then** the strong error-shaped lines are still returned in log order and no region is invented
- **Test:** tests/test_pipeline_failure_error_block.py::test_a_log_without_group_markers_still_yields_a_diagnosis

#### Scenario: the ledger row records the diagnosis additively and the re-diagnosis pass reuses it

- **Given** the recorded `gh` fixture (a run whose failing job answers the planted log and a steps
  list) and an empty ledger
- **When** the sweep files the run and a later sweep re-reads an `undiagnosed` row
- **Then** the new row carries `failing_steps` and `error_region` beside its existing keys, no
  stored value of any earlier row changed, and the re-diagnosis block was extracted through the
  same seam
- **Test:** tests/test_pipeline_failure_error_block.py::test_the_ledger_row_carries_the_diagnosis_and_re_diagnosis_reuses_the_seam
