## ADDED Requirements

### Requirement: The extracted block presents the failing region first and marks filler as filler

`extract_error_block` SHALL present the error-shaped lines of the FAILING region — the log region
carrying GitHub's own `##[error]` decoration, in log order — FIRST, then the strongest shapes from
other step regions, then a passing module's soft `FAIL`/`FAILED` chatter. When any line outside the
failing region is quoted, the block SHALL insert exactly one `[filer]` marker line between the
region's lines and the rest, naming how many filler lines follow and which region they are NOT from.
Selection (the tier order, de-duplication, the `MAX_ERROR_LINES` cap), the end-of-block drop note
and the ungrouped-log fallback SHALL keep their current behaviour.

#### Scenario: a thin failing region is not padded with earlier chatter

- **Given** a planted job log whose earlier regions hold a passing module's
  `FAIL:`/`PASSED … | FAILED 0` chatter and whose LAST `##[error]` region holds only the two lines
  that diagnose the run
- **When** the real filer extracts that log
- **Then** the block begins with the failing region's two lines, the chatter appears only after an
  explicit `[filer]` filler marker, and the block stays within `MAX_ERROR_LINES`
- **Test:** tests/test_pipeline_failure_issue.py::test_a_thin_failing_region_is_quoted_before_earlier_chatter

#### Scenario: a region that genuinely holds the diagnosis keeps log order

- **Given** a planted log whose only error-shaped lines are inside the failing region
- **When** the real filer extracts that log
- **Then** the block is exactly those lines in log order, with no filler marker and no drop note
- **Test:** tests/test_pipeline_failure_issue.py::test_a_region_holding_the_diagnosis_keeps_today_s_order

#### Scenario: the #1098 guard asserts the per-group order

- **Given** the measured tail of qa-validate run 43725338063 (succeeded regions full of chatter,
  then the `Run make openspec-check` region carrying the refusal)
- **When** the real filer extracts that log
- **Then** every failing-region line precedes every other-region line, each group keeps its log
  order, and the filler marker sits between them
- **Test:** tests/test_pipeline_failure_error_block.py::test_chatter_dropped_for_room_is_announced_in_the_block
