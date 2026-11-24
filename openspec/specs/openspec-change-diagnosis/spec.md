# openspec-change-diagnosis Specification

## Purpose
TBD - created by archiving change openspec-active-twin-diagnosis. Update Purpose after archive.

## Requirements

### Requirement: An ACTIVE twin of an ARCHIVED change is diagnosed, not mis-reported

A tree that carries BOTH `openspec/changes/<name>/` and
`openspec/changes/archive/<name>/` SHALL be FAILED by the reference gate with a
message naming BOTH paths and the exact remedy (`git rm -r
openspec/changes/<name>` then `make openspec-index`). `change_for(name)` SHALL
return the ACTIVE directory whenever one exists, and `archived_twin(name)` SHALL
name the archived copy. A change that exists ONLY in the archive SHALL stay
excluded from the scan.

#### Scenario: An ACTIVE twin is named with both paths and the remedy

- **Given** a change directory present in BOTH `openspec/changes/<name>/` and
  `openspec/changes/archive/<name>/`
- **When** `check_openspec_test_lines.check_all` runs over that tree
- **Then** the gate exits non-zero and its output names both
  `openspec/changes/<name>` and `openspec/changes/archive/<name>` plus the
  `git rm -r` / `make openspec-index` remedy
- **Test:** tests/test_openspec_spec_tests.py::test_an_active_twin_of_an_archived_change_is_diagnosed

#### Scenario: The seam separates the two copies

- **Given** the same twin tree
- **When** `change_for(name)` and `archived_twin(name)` are called
- **Then** `change_for` returns the ACTIVE path and `archived_twin` returns the
  ARCHIVED path
- **Test:** tests/test_openspec_spec_tests.py::test_an_active_twin_of_an_archived_change_is_diagnosed

#### Scenario: An ARCHIVED-only change stays excluded

- **Given** a change present only under `openspec/changes/archive/<name>/`
- **When** the gate runs over that tree
- **Then** it is green and never reports the archived change
- **Test:** tests/test_openspec_spec_tests.py::test_archived_change_is_ignored

#### Scenario: The shipped tree still resolves and the gate stays wired

- **Given** this repository's own tree and Makefile
- **When** the gate runs over the real tree and the CLI runs as CI runs it
- **Then** every active change's `- **Test:**` reference resolves, no NOTE line is
  printed, and the Makefile wiring holds
- **Test:** tests/test_openspec_spec_tests.py::test_real_repo_references_resolve_and_the_gate_is_wired
