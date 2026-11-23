## ADDED Requirements

### Requirement: A derived needle already present in the section is refused

`owed_row_derive.derive_rows` SHALL answer `[]` when the DERIVED needle already appears inside the declared section's line span, so a module name the section already carries cannot satisfy an EXTENSION row.

#### Scenario: The extension shape that laundered #1357

- **Given** a Done-when naming `tests/test_watch_monitor.py` and a rulebook whose §8 already names that module
- **When** `derive_rows` runs
- **Then** it answers `[]` — no marker is invented
- **Test:** tests/test_filer_owed_rows.py::test_a_derived_needle_already_in_the_section_is_refused

#### Scenario: The real rulebook

- **Given** the real `AGENTS.md`, where §8 names `tests/test_watch_monitor.py`
- **When** the same sentence is derived
- **Then** the answer is `[]`
- **Test:** tests/test_filer_owed_rows.py::test_a_derived_needle_already_in_the_section_is_refused

#### Scenario: Not vacuous

- **Given** a section that does NOT already name the module
- **When** the same sentence is derived
- **Then** the declaration is returned unchanged
- **Test:** tests/test_filer_owed_rows.py::test_a_derived_needle_already_in_the_section_is_refused

### Requirement: The explicit field and the other refusals are unchanged

The `- **Owed-row:**` field path, the `NO SUCH SECTION` refusal and the "no section stated / no identifier named" refusals SHALL keep their current behaviour.

#### Scenario: The derivation still states only what the text names

- **Given** the shipped derivation guards
- **When** the module's suite runs
- **Then** the explicit-field, missing-section and missing-identifier behaviours are unchanged
- **Test:** tests/test_filer_owed_rows.py::test_the_derivation_states_only_what_the_text_names
