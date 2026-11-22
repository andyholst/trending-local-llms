## ADDED Requirements

### Requirement: The nerve credential guard honours the sanctioned test-value marker

`scripts/nerve_key_check.py` SHALL import the marker constant
`TEST_VALUE_MARKER` from `scripts/check_secret_output.py` and SHALL NOT re-spell
the literal. `scan_tree` SHALL skip the credential-SHAPE scan for any tracked
file whose text carries that marker, so a deliberate test value marked per the
rulebook passes `make nerve-check` exactly as it passes
`make check-secret-output`.

#### Scenario: A marked test file carrying a key-shaped literal is exempt

- **Given** a tracked file under a scanned directory whose text carries
  `secret-output: test value` and a `sk-…` literal
- **When** `scan_tree()` walks the tree
- **Then** no finding names that file
- **Test:** tests/test_nerve_key_wiring.py::test_marked_test_value_file_is_exempt

#### Scenario: The same literal in an unmarked file is still a finding

- **Given** a tracked file under a scanned directory with the same `sk-…` literal
  and no marker
- **When** `scan_tree()` walks the tree
- **Then** a finding names that file
- **Test:** tests/test_nerve_key_wiring.py::test_unmarked_test_value_file_is_still_a_finding

#### Scenario: The marker is one imported definition

- **Given** the nerve guard module and the secret-output module
- **When** the test compares them
- **Then** `nerve_key_check.TEST_VALUE_MARKER` equals
  `check_secret_output.TEST_VALUE_MARKER` and the literal appears nowhere in
  `scripts/nerve_key_check.py`
- **Test:** tests/test_nerve_key_wiring.py::test_the_marker_is_imported_not_respelled
