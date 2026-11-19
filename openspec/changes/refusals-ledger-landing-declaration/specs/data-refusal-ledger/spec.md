## ADDED Requirements

### Requirement: Only a declared landing stage writes the refusals ledger

`scripts/update_trending.py` SHALL land ingest refusals in `data/refusals.json` only when the
run declares itself a delivery stage — `--land-refusals` on the command line, or
`declare_refusals_landing(True)` in-process, or a caller that names its own ledger path. A
pass that declares nothing SHALL record nothing: the seam prints every refusal, counts it, and
leaves the tracked file byte-identical.

#### Scenario: An undeclared full ingest pass lands no refusal

- **Given** a real git checkout of HEAD (`git archive` + `git init` + one seed commit) holding
  the shipped `data/refusals.json` and the shipped `data/raw` snapshots
- **When** `python3 scripts/update_trending.py --since 2000-01-01T00:00:00Z` runs with no
  landing declaration
- **Then** the run exits 0, `git status --porcelain -- data/refusals.json` is empty, and the
  ledger on disk is record-for-record identical to the one HEAD carries
- **Test:** tests/test_refusals_land_declaration.py::test_an_undeclared_full_ingest_lands_no_refusals

#### Scenario: A declared delivery stage lands the ledger and only grows counters

- **Given** the same scratch checkout, with the ledger's records and observation totals read
  before the run
- **When** `python3 scripts/update_trending.py --since 2000-01-01T00:00:00Z --land-refusals`
  runs (the shape of the Makefile's `_merge` delivery recipe)
- **Then** the run announces its declaration, `git status --porcelain` names
  `data/refusals.json`, no record is removed, and the sum of `seen_count` is larger than
  before the run
- **Test:** tests/test_refusals_land_declaration.py::test_a_declared_delivery_stage_lands_the_ledger

### Requirement: A pass that lands nothing says so loudly

A non-declared pass SHALL print every refusal line it printed before, SHALL keep the run
total line's shape (`[ingest] N measurement(s) refused at ingest this run`), and SHALL state
in that line and in each per-file summary that the refusals were NOT landed and why, naming
the flag a delivery must pass.

#### Scenario: The undeclared summary names the ledger and denies the record

- **Given** the scratch checkout and the undeclared full ingest pass
- **When** its stdout is read
- **Then** at least one `[ingest] REFUSED` line and one per-file
  `refusal(s) NOT landed in the refusals ledger` line appear, exactly one run-total line
  appears, and that line carries `NONE landed in data/refusals.json`, `no declared` and
  `--land-refusals`
- **Test:** tests/test_refusals_land_declaration.py::test_an_undeclared_pass_still_reports_every_refusal

### Requirement: A dry-run never lands, and cannot claim it may

`--dry-run` writes nothing, so a run that pairs it with `--land-refusals` SHALL be refused
with exit 2 naming both flags and the issue, and SHALL write nothing. A `--dry-run` pass on
its own SHALL exit 0, refuse loudly in the log, and leave the whole tracked tree clean.

#### Scenario: The contradictory pair is refused

- **Given** the scratch checkout
- **When** `python3 scripts/update_trending.py --dry-run --since … --land-refusals` runs
- **Then** it exits 2, its stderr names `--dry-run`, `--land-refusals` and `#1155`,
  `git status --porcelain` is empty, and the ledger equals the shipped one
- **Test:** tests/test_refusals_land_declaration.py::test_a_dry_run_cannot_declare_a_landing

#### Scenario: A dry-run pass leaves the whole tree byte-identical

- **Given** the scratch checkout
- **When** `python3 scripts/update_trending.py --dry-run --since 2000-01-01T00:00:00Z` runs
- **Then** it exits 0, prints `[ingest] REFUSED` lines, and `git status --porcelain` for the
  whole tree is empty
- **Test:** tests/test_refusals_land_declaration.py::test_a_dry_run_writes_nothing_at_all

### Requirement: The delivery recipes declare the landing and the validation recipes do not

The `Makefile` recipes that fold gathered raw into the store (`_merge`, `_merge-fetch`, the
`_fix` merge) SHALL carry `--land-refusals`; no recipe that runs a `--dry-run` ingest and no
`_validate-*` recipe SHALL carry it. The suite modules that measured the churn SHALL pass
under the rule and leave a scratch checkout of HEAD clean.

#### Scenario: The wiring is read from the Makefile text

- **Given** the repository's own `Makefile`
- **When** each named recipe's tab-indented lines are read
- **Then** `_merge`, `_merge-fetch` and `_fix` each contain `--land-refusals` alongside
  `scripts/update_trending.py`, at least one `--dry-run` ingest recipe exists, and neither it
  nor any `_validate-*` recipe contains `--land-refusals`
- **Test:** tests/test_refusals_land_declaration.py::test_the_makefile_delivery_recipes_declare_the_landing

#### Scenario: The three modules that grew the shipped ledger leave the tree clean

- **Given** a scratch checkout of HEAD
- **When** `tests/test_engine_registry.py`, `tests/test_engine_aliases.py` and
  `tests/test_measurement_attribution.py` are each run the way `make test` runs them
- **Then** every module exits 0 and `git status --porcelain` for the whole tree is empty
- **Test:** tests/test_refusals_land_declaration.py::test_the_measured_suite_modules_leave_the_tree_clean
