# openspec-test-lines-gate — delta

## MODIFIED Requirements

### Requirement: a `- **Test:**` citation must resolve or the gate refuses

Every `- **Test:**` line in an ACTIVE change's capability specs must name a `<path>::<symbol>` reference that resolves against the tree (the `<path>` exists; for a Python module, the `<symbol>` is defined top-level in it). A `- **Test:**` line that names no such reference — prose, or a bare path with no `::symbol` — is a FAILURE, not a tolerated note: the gate refuses (exit 1) naming the change, the spec file:line and the unresolved citation.

#### Scenario: a prose Test line refuses the gate

- **Given** an ACTIVE change whose spec carries a resolvable `tests/ok.py::test_ok` citation AND a `tests/ok.py (the §6b list — no symbol)` line
- **When** `scripts/check_openspec_test_lines.py` runs over the tree
- **Then** the gate exits non-zero and prints a FAIL naming the no-symbol line as a `- **Test:**` line that names no `<path>::<test>` reference

- **Test:** tests/test_openspec_spec_tests.py::test_a_prose_test_line_refuses_the_gate

#### Scenario: an ACTIVE change with no Test line at all refuses the gate

- **Given** an ACTIVE change whose only spec has scenarios but no `- **Test:**` line
- **When** the gate runs
- **Then** the gate exits non-zero naming the change as carrying nothing to resolve

- **Test:** tests/test_openspec_spec_tests.py::test_a_spec_with_no_test_lines_refuses_the_gate

#### Scenario: fully resolvable citations stay green with no notes

- **Given** an ACTIVE change whose every `- **Test:**` line resolves
- **When** the gate runs
- **Then** it exits 0 and its output contains no NOTE line and no FAIL line

- **Test:** tests/test_openspec_spec_tests.py::test_a_resolvable_reference_is_green

## ADDED Requirements

### Requirement: the shipped tree carries zero unresolved citations

`make openspec-spec-tests-check` over this repository's own ACTIVE changes must exit 0 with NO NOTE and NO FAIL line in its output — every active scenario's lock is a resolvable reference.

#### Scenario: the real tree passes the strict gate

- **Given** this repository's ACTIVE changes (`weekly-security-scan`, `attribution-joint-figure-alias`, this change)
- **When** `python3 scripts/check_openspec_test_lines.py` runs
- **Then** it exits 0 and prints no NOTE line

- **Test:** tests/test_openspec_spec_tests.py::test_real_repo_references_resolve_and_the_gate_is_wired
