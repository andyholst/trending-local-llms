# openspec-index-drift

## ADDED Requirements

### Requirement: The drift report prints the one measure and never gates

`scripts/openspec_index.py --drift` MUST print exactly one line, `drift=<n>`, where `<n>`
is the SAME count `index_drift()` already feeds `--check`, and MUST exit 0 for any drift on
a readable tree. It is a REPORT beside the gate, not a second verdict:
`MAX_OPENSPEC_INDEX_DRIFT`, the WARN branch and `--check`'s exit codes are unchanged. A
missing or unreadable `OPENSPEC.md` MUST be loud instead — a stderr message naming
`make openspec-index`, no stdout, exit 2.

#### Scenario: the count-line-only drift of master cb139e7c

- **Given** a tree whose committed index rows are complete but whose count line lags disk
  by one archive (the measured `cb139e7c` shape)
- **When** the real CLI runs `--drift`
- **Then** it exits 0 and stdout is exactly `drift=1\n`
- **Test:** tests/test_openspec_index_drift.py::test_drift_report_exits_0_and_prints_the_one_measure

#### Scenario: a current index reports zero, and row drift is counted too

- **Given** an index that matches its tree, and separately an index that also lost one row
- **When** the real CLI runs `--drift` on each
- **Then** the first prints `drift=0` and the second prints `drift=2` (missing row + count
  line), both exit 0
- **Test:** tests/test_openspec_index_drift.py::test_drift_report_exits_0_and_prints_the_one_measure

#### Scenario: the gate itself is untouched

- **Given** the same drifted fixture
- **When** `--check` runs
- **Then** it still exits 0 with a WARN, and a missing index still exits 1 while `--drift`
  exits 2 with no stdout
- **Test:** tests/test_openspec_index_drift.py::test_a_missing_index_is_loud_in_the_report_mode

### Requirement: A green push with reported drift wakes the index-repair keeper

`.github/workflows/qa-validate.yml` MUST publish the drift as an allowlisted `validate`
output key read from a step that calls `make openspec-index-drift`, and the `index-repair`
job's `if:` MUST fire when that key is not `'0'` as well as on `failure()`, still only on a
push to `master`. `failure()` stays, so a red validate whose drift step never ran behaves
exactly as before.

#### Scenario: the keeper trigger carries the drift clause

- **Given** the real `qa-validate.yml`
- **When** the guard reads the `index-repair` job's `if:` clause
- **Then** it carries `needs.validate.outputs.index_drift != '0'` beside `failure()`,
  `github.event_name == 'push'` and `refs/heads/master`, and names no `pull_request`
- **Test:** tests/test_openspec_index_drift.py::test_a_green_push_with_drift_wakes_the_index_repair_keeper

#### Scenario: validate publishes the key through make

- **Given** the real `qa-validate.yml` `validate` job
- **When** its text is read
- **Then** it declares `index_drift: ${{ steps.index-drift.outputs.drift }}`, runs
  `make openspec-index-drift`, and writes only the parsed `drift=` key into `$GITHUB_OUTPUT`
- **Test:** tests/test_openspec_index_drift.py::test_a_green_push_with_drift_wakes_the_index_repair_keeper

### Requirement: The drift target is wired and registered

The Makefile MUST carry a real `.PHONY` `openspec-index-drift` target whose recipe runs
`$(PYTHON_RUN) python3 scripts/openspec_index.py --drift`; the `validate` job MUST call it;
and `scripts/master_alarm.py::GATES` MUST name it, so `master_alarm.unchecked_gates()`
over the validate job is empty and the report sits on the ALARM list (it regenerates
nothing and never gates a merge).

#### Scenario: the wiring is read back from the tree

- **Given** the real `Makefile`, `qa-validate.yml` and `scripts/master_alarm.py`
- **When** the guard derives the target, its `.PHONY` entry, the validate call and the
  registry coverage
- **Then** all four hold and `GATES["openspec-index-drift"] == ("alarm", "master-alarm")`
- **Test:** tests/test_openspec_index_drift.py::test_the_drift_target_is_registered_and_called_through_make

### Requirement: The tolerance still fails the gate beyond its bound

The additive report MUST NOT change the existing gate: at exactly
`MAX_OPENSPEC_INDEX_DRIFT` differing changes `--check` still exits 0 with a WARN, and one
more still exits 1 with a FAIL naming the count.

#### Scenario: the shared constant boundary is unchanged

- **Given** a fixture with exactly `MAX_OPENSPEC_INDEX_DRIFT` changed rows, and one with a
  single row more
- **When** `--check` runs on each
- **Then** the first exits 0 (WARN) and the second exits 1 (FAIL naming the exceeded
  tolerance)
- **Test:** tests/test_openspec_index.py::test_drift_boundary_is_the_shared_constant
