# bot-coordination

## ADDED Requirements

### Requirement: the refresh PR body carries the run's window

The `aggregate` job SHALL lead the PR body it opens with a window block composed from the run's REAL
job timestamps, written by the shared marker helper.

#### Scenario: a real run renders exactly the expected block

- **GIVEN** a recorded capture of an actual refresh run (its `run_started_at` and each job's
  `started_at`),
- **WHEN** the composer renders the block,
- **THEN** the marker names the run and carries its start, every leg carries that job's recorded
  start, and the run URL is present.

- **Test:** `tests/test_refresh_run_block.py::test_the_real_run_renders_exactly_the_expected_block`

#### Scenario: the shared parser reads the block

- **GIVEN** a rendered block,
- **WHEN** `scripts/bot_markers.py` parses it,
- **THEN** it resolves to the `refresh-bot`/`run` marker with the run id and a parseable timestamp.

- **Test:** `tests/test_refresh_run_block.py::test_the_shared_parser_reads_the_block`

### Requirement: legs are identified by the job name the API returns

The composer SHALL match each leg by the job NAME, not by position or a hardcoded index, and SHALL
print `unknown` for a leg it cannot see rather than inventing a time.

#### Scenario: a reordered or unknown job is not mislabelled

- **GIVEN** a job list whose legs are out of order, one leg missing, and a non-leg `search (...)`
  job present,
- **WHEN** the legs are read,
- **THEN** order does not matter, the non-leg is not a leg, and the missing one reads `unknown`.

- **Test:** `tests/test_refresh_run_block.py::test_legs_come_from_the_real_job_names`

### Requirement: a window that cannot be read is loud

A failed `gh` read SHALL raise rather than printing a block with no numbers; with no run context at
all (a local run) the answer SHALL be empty.

#### Scenario: a failed read does not print a clean window

- **GIVEN** a `gh` on PATH that exits non-zero,
- **WHEN** the block is composed,
- **THEN** the command exits non-zero naming the failure, and a run with no context yields `''`.

- **Test:** `tests/test_refresh_run_block.py::test_a_run_we_cannot_read_is_loud`

### Requirement: the block is stamped only where an artifact exists

The block SHALL be composed into the PR body only on the path that opens a PR, so a run with no new
data stamps nothing, and the gap issue SHALL carry the same block from the same composer.

#### Scenario: no data means no block

- **GIVEN** the `aggregate` PR step,
- **WHEN** its script is read,
- **THEN** `make refresh-run-block` and `--body-file` appear inside the data-changed branch (after
  the `else`), and the hand-written `--body "…"` is gone.

- **Test:** `tests/test_refresh_run_block.py::test_the_workflow_stamps_the_pr_body_and_not_a_no_data_run`

#### Scenario: the gap issue carries the same block

- **GIVEN** `scripts/data_gap_analysis.py`,
- **WHEN** it builds the issue body,
- **THEN** it embeds `refresh_run_block.current_block()` at the TOP of the body.

- **Test:** `tests/test_refresh_run_block.py::test_the_gap_issue_carries_the_same_block`

### Requirement: the registry knows the writer exists

`scripts/bot_markers.py` SHALL list `(refresh-bot, run)` as written.

#### Scenario: the declared marker becomes written

- **GIVEN** the registry,
- **WHEN** its `WRITTEN` and `DECLARED_BY` sets are read,
- **THEN** `(refresh-bot, run)` is in `WRITTEN`, absent from `DECLARED_BY`, and its name appears in
  the tree.

- **Test:** `tests/test_bot_markers.py::test_every_written_marker_has_a_writer`
