# stage-wiring

## ADDED Requirements

### Requirement: The stage-wiring rule has one reader

`tests/test_validate.py` MUST read the validator's registered stages and the Makefile's `--only`
selections through `scripts/architecture_check.py`, never with a parser of its own, and MUST prove
the two readers agree.

#### Scenario: a stage loses every selection

- **Given** a Makefile whose `--only` lists no longer name `removal`
- **When** the wiring test runs
- **Then** it fails naming the stage and the stages it did find
- **Test:** tests/test_validate.py::test_every_check_is_wired_to_a_stage_and_a_makefile_target

#### Scenario: the two readers agree

- **Given** the shipped validator and Makefile
- **When** the wiring test compares `validate_stages()` with the test's own registration parse
- **Then** the sets are identical
- **Test:** tests/test_validate.py::test_every_check_is_wired_to_a_stage_and_a_makefile_target
