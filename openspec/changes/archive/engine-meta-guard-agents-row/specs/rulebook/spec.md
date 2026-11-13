# rulebook

## ADDED Requirements

### Requirement: The rulebook names the engine-metadata commit-step guard

`AGENTS.md` §8 MUST carry a row naming
`tests/test_engine_registry.py::test_capture_meta_keeps_the_fixture_covering_the_registry`
beside the existing `tests/test_engine_registry.py` rows, stating the failure it catches
(the engine-metadata fixture dropped from the refresh commit step's `git diff --quiet` change
check or its `git add` list) and citing the issue (#745) and the change that owed it
(#505 / PR #744).

#### Scenario: a reader asks what guards the engine-metadata capture

- **Given** `AGENTS.md` §8
- **When** the `tests/test_engine_registry.py` rows are read
- **Then** one row names `test_capture_meta_keeps_the_fixture_covering_the_registry`, names
  both commit-step lists (`git diff --quiet` and `git add`), and cites #745 and #505
- **Test:** tests/test_agents_rows.py::main

#### Scenario: a row may not describe a guard that no longer exists

- **Given** the §8 row naming the engine-metadata guard
- **When** the guard is renamed away from `tests/test_engine_registry.py`, or the refresh
  commit step drops the fixture from either of its lists
- **Then** `tests/test_agents_rows.py` fails, naming the missing guard or the dropped list —
  a row that describes nothing is the #369 defect shape, not a pass
- **Test:** tests/test_agents_rows.py::main
