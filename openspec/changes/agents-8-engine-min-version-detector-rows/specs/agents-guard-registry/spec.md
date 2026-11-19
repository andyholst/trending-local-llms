# agents-guard-registry

## ADDED Requirements

### Requirement: The §8 row the #1020 engine-build detector owed names all three guards

`AGENTS.md` §8 MUST carry one row for the drift class issue #1020 measured (an engine NAME beside
a throughput figure mined as an engine BUILD), and that row MUST name both modules the guards live
in (`tests/test_engine_min_version_ingest.py`, `tests/test_data_gap_analysis.py`) and all three
guards (`test_bare_engine_names_beside_throughput_figures_never_claim`,
`test_explicit_build_phrases_still_claim`,
`test_engine_min_version_candidates_are_engine_names_not_build_claims`), citing the issue and the
PR that measured the failure. `tests/test_agents_rows.py` MUST fail when that row is removed,
stops naming a guard, or names a guard that is no longer a function of the module it names.

#### Scenario: the row is present and names every guard it owes

- **Given** the §8 regression-guard table on a tree where #1020's fix has merged
- **When** the row naming `test_bare_engine_names_beside_throughput_figures_never_claim` is read
- **Then** the same row names `test_explicit_build_phrases_still_claim`, names
  `test_engine_min_version_candidates_are_engine_names_not_build_claims`, cites #1020 and PR #1127,
  and states the throughput-adjacency drift class it catches
- **Test:** `tests/test_agents_rows.py::test_the_engine_min_version_bare_engine_name_row_is_written`

#### Scenario: the guards the row names are real functions of those modules

- **Given** the two modules the row names
- **When** the pin resolves each guard it cites
- **Then** each guard is a `def test_…(` in the module the row names, so renaming or deleting one
  turns the pin RED instead of leaving a rulebook row that describes nothing
- **Test:** `tests/test_agents_rows.py::test_the_engine_min_version_bare_engine_name_row_is_written`

#### Scenario: a removed row is loud

- **Given** `AGENTS.md` §8 with that row deleted (the state #1128 found on the base)
- **When** `tests/test_agents_rows.py` runs
- **Then** it fails naming the missing guard names, and `make test` goes red
- **Test:** `tests/test_agents_rows.py::test_the_engine_min_version_bare_engine_name_row_is_written`
