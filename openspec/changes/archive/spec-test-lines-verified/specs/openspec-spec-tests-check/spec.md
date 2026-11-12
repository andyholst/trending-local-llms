# openspec-spec-tests-check

## ADDED Requirements

### Requirement: a spec's `- **Test:**` reference must resolve to a real target

`make openspec-spec-tests-check` SHALL, for every ACTIVE (non-archived) change,
read every `- **Test:**` line in its capability specs and resolve each
`<path>::<test>` reference against the tree: `<path>` SHALL exist, and when it
is a tracked Python module the `<test>` SHALL be a name defined top-level in it
(a `def`/`class`, or a module-level assignment). A reference that fails SHALL be
reported naming the change, the spec `file:line` (scenario) and the missing
target, and SHALL make the check exit non-zero — so a scenario citing a test
that was never written turns the gate red instead of passing silently.

#### Scenario: a scenario cites a Python test that is never written

- **GIVEN** an active change whose spec carries `- **Test:** tests/test_agents_rows.py::test_the_footprint_sentence_names_every_dimension`
  (the shipped *measured* failure: the file exists on origin/master but defines
  no such symbol)
- **WHEN** the gate runs
- **THEN** it exits non-zero and names the change, the scenario line and the
  missing symbol

- **Test:** `tests/test_openspec_spec_tests.py::test_the_shipped_reference_is_red`

#### Scenario: a scenario cites a file that does not exist

- **GIVEN** an active change whose spec cites `tests/nope.py::test_anything`
- **WHEN** the gate runs
- **THEN** it exits non-zero naming the change, the scenario and the missing file

- **Test:** `tests/test_openspec_spec_tests.py::test_a_missing_file_is_red`

#### Scenario: a resolvable reference is green

- **GIVEN** an active change whose spec cites a `path::test` whose file exists
  and whose symbol is defined top-level
- **WHEN** the gate runs
- **THEN** it exits 0 and does not name the change as failing

- **Test:** `tests/test_openspec_spec_tests.py::test_a_resolvable_reference_is_green`

### Requirement: the scan is not vacuous and never invents a resolution

A `- **Test:**` line that names no `path::test` reference (prose, or a bare
path with no `::symbol`) SHALL be REPORTED, never treated as resolved; a change
whose specs carry no `- **Test:**` lines at all SHALL be reported as having
nothing to resolve so a vacuous scan cannot read as verified; and an ARCHIVED
change SHALL be excluded (its references are not re-checked).

#### Scenario: a prose Test line is reported, not treated as resolved

- **GIVEN** an active change whose spec has `- **Test:** tests/test_workflows.py (the §6b list)`
  (no `::symbol`)
- **WHEN** the gate runs
- **THEN** it exits 0 but reports the line as naming no resolvable reference

- **Test:** `tests/test_openspec_spec_tests.py::test_a_prose_test_line_is_reported_not_resolved`

#### Scenario: a spec with no Test references is reported as nothing to resolve

- **GIVEN** an active change whose specs contain no `- **Test:**` lines
- **WHEN** the gate runs
- **THEN** it exits 0 and reports the change as carrying no resolvable reference

- **Test:** `tests/test_openspec_spec_tests.py::test_a_spec_with_no_test_lines_is_reported`

#### Scenario: an archived change is not re-checked

- **GIVEN** an archived change whose spec cites a reference that no longer resolves
- **WHEN** the gate runs
- **THEN** it exits 0 and never reports that change

- **Test:** `tests/test_openspec_spec_tests.py::test_archived_change_is_ignored`

### Requirement: the real repository is currently resolvable, and the gate is wired

The gate SHALL pass on this repository's own tree (every ACTIVE change's
references resolve), and SHALL be reachable: the `Makefile` SHALL define
`openspec-spec-tests-check`, it SHALL be a dependency of `openspec-check`, the
script SHALL run it, and the test file SHALL be part of `make test` (rule 6d).

#### Scenario: the real tree passes and the gate is wired into CI

- **GIVEN** this repository's real `openspec/changes` and `scripts/`
- **WHEN** the gate runs over the tree and the Makefile wiring is read
- **THEN** it exits 0, the target is defined and bundled in `openspec-check`, and
  the test module is listed by the runner

- **Test:** `tests/test_openspec_spec_tests.py::test_real_repo_references_resolve_and_the_gate_is_wired`
