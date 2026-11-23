## ADDED Requirements

### Requirement: Small index drift is tolerated and named

`scripts/openspec_index.py --check` SHALL exit 0 with a `WARN` naming the drift when the committed `OPENSPEC.md` differs from the disk render by at most `MAX_OPENSPEC_INDEX_DRIFT` (25) changes, counted as rows on disk with no row + rows for changes that no longer exist + rows whose data changed + the count-line drift. It SHALL exit 1 with the existing FAIL text plus the count when more than that differ.

#### Scenario: A one-change count-line drift

- **Given** a committed index whose only drift is its archived/active count line
- **When** `--check` runs
- **Then** it exits 0 with a WARN naming the count line, and does not blame the rows
- **Test:** tests/test_openspec_index.py::test_a_small_count_line_drift_warns_and_is_not_blamed_on_the_rows

#### Scenario: Exactly at the threshold

- **Given** exactly MAX_OPENSPEC_INDEX_DRIFT differing changes
- **When** `--check` runs
- **Then** it exits 0 with a WARN naming the drift
- **Test:** tests/test_openspec_index.py::test_drift_boundary_is_the_shared_constant

#### Scenario: One change over the threshold

- **Given** MAX_OPENSPEC_INDEX_DRIFT + 1 differing changes
- **When** `--check` runs
- **Then** it exits 1 and the FAIL text names the count and the tolerated threshold
- **Test:** tests/test_openspec_index.py::test_drift_boundary_is_the_shared_constant

#### Scenario: Every category counts once

- **Given** a missing row, an extra row, a changed row and a moved count line
- **When** the drift is measured
- **Then** each contributes one difference to the count
- **Test:** tests/test_openspec_index.py::test_index_drift_counts_each_category_once

### Requirement: A missing index never passes

A missing `OPENSPEC.md` has nothing to compare, so `--check` SHALL exit 1 regardless of the tolerance, naming the regeneration remedy.

#### Scenario: No committed index at all

- **Given** change directories on disk and no `OPENSPEC.md`
- **When** `--check` runs
- **Then** it exits 1 naming `make openspec-index`
- **Test:** tests/test_openspec_index.py::test_a_missing_index_still_fails

### Requirement: The keeper shares the same threshold

`scripts/openspec_index_repair.py` SHALL classify drift with the generator's ONE `index_drift()` and `MAX_OPENSPEC_INDEX_DRIFT`, so a drift the gate only warns about is still named, counted and rewritten rather than left to accumulate.

#### Scenario: A tolerated drift is still classified and repaired

- **Given** complete changes and a small index drift
- **When** the keeper classifies this tree
- **Then** it reports `DRIFT=index-only`, names the count and the shared threshold, and rewrites an index that passes `--check`
- **Test:** tests/test_openspec_index_repair.py::test_a_tolerated_drift_is_still_classified_and_repaired
