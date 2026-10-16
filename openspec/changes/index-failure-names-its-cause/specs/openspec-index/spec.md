# openspec-index

## ADDED Requirements

### Requirement: a stale index names the drift it actually found

`make openspec-index-check` SHALL fail when the committed `OPENSPEC.md` differs
from what `--write` would produce, and its message SHALL name the drift it found:
changes on disk with no row, rows for changes that no longer exist, the **count
line** when its numbers drifted (quoting the number the disk needs), and the rows
whose data changed. It SHALL NOT attribute a count-line drift to the rows, and it
SHALL NOT assert a cause it did not find.

#### Scenario: a count-line drift is named as the count line

- **GIVEN** a committed index whose rows are all present and identical and whose
  only drift is the `Active changes: **N**` line (measured on `master`, run
  38865506979: the file said 30, the tree held 31)
- **WHEN** `--check` runs
- **THEN** it exits non-zero, names the count line and the number the disk needs,
  and does NOT claim the rows' data changed

- **Test:** `tests/test_openspec_index.py::test_a_stale_count_line_is_named_and_not_blamed_on_the_rows`

#### Scenario: a row whose data moved is named

- **GIVEN** a change whose `tasks.md` moved after the index was written, so its
  row's task progress no longer matches
- **WHEN** `--check` runs
- **THEN** it exits non-zero and names that change among the rows whose data changed

- **Test:** `tests/test_openspec_index.py::test_a_row_whose_data_moved_is_named`

#### Scenario: a change with no row is named

- **GIVEN** a change directory on disk that has no row in the index
- **WHEN** `--check` runs
- **THEN** it exits non-zero and lists the change as having no row

- **Test:** `tests/test_openspec_index.py::test_change_with_no_row_fails_the_check`

### Requirement: write and check agree

`--write` SHALL produce exactly the file `--check` accepts, so a regenerated index
is never stale, and this repository's committed index SHALL be current.

#### Scenario: a regenerated index passes the check

- **GIVEN** a fixture change tree with no index yet
- **WHEN** `--write` runs and then `--check` runs
- **THEN** both exit 0

- **Test:** `tests/test_openspec_index.py::test_write_then_check_is_green`

#### Scenario: the committed index is current

- **GIVEN** this repository's real `OPENSPEC.md` and `openspec/changes/`
- **WHEN** the check runs and the rows are compared with the directories
- **THEN** the check exits 0 and every change directory has a row

- **Test:** `tests/test_openspec_index.py::test_real_repo_index_is_current_and_lists_every_change`
