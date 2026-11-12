# duplicate-change-for-one-edit

## ADDED Requirements

### Requirement: two active changes must not declare the same requirement heading

The duplication gate SHALL fail, exit 1, when two DIFFERENT active changes each
carry a capability Requirement whose heading is the SAME (case- and
whitespace-normalized) under the SAME kind — both `ADDED` (two changes both
proposing the same new rule) or both `MODIFIED` (two changes both rewriting the
same existing rule) — and SHALL name both changes, the capability and the
heading in its report. It MUST NOT flag an `ADDED`∩`MODIFIED` pairing of the
same heading across two changes: that is a refinement chain, not a duplicate.
`tests/test_openspec_duplicate_check.py` drives the real script and must
exist to lock this behaviour.

#### Scenario: two ADDED headers of the same rule are named

- **Given** ACTIVE changes `agents-md-footprint-dimensions` and
  `the-owed-section-4-sentence`, each declaring an `ADDED` requirement headed
  `§4 names every optional per-measurement footprint dimension`
- **When** the gate runs over the tree
- **Then** it exits non-zero, names both changes, the capability, and the shared heading

- **Test:** tests/test_openspec_duplicate_check.py::test_duplicate_added_heading_fails_naming_both

#### Scenario: ADDED then MODIFIED of one heading is a chain, not a duplicate

- **Given** ACTIVE change BUILD adding a requirement headed
  `the live check's verdict names the failure` and change REFINE declaring the
  SAME heading as `MODIFIED`
- **When** the gate runs
- **Then** it exits 0 and does not report either change

- **Test:** tests/test_openspec_duplicate_check.py::test_add_then_modify_is_a_chain_not_a_duplicate

#### Scenario: two MODIFIED rewrites of the same rule are named

- **Given** ACTIVE changes A and B both declaring the SAME heading as
  `MODIFIED`
- **When** the gate runs
- **Then** it exits non-zero and names both changes

- **Test:** tests/test_openspec_duplicate_check.py::test_duplicate_modified_heading_fails_naming_both

#### Scenario: the real repository is green

- **Given** this repository's actual `openspec/changes` tree
- **When** the gate runs over it
- **Then** it exits 0 (no two active changes today share a same-kind heading)

- **Test:** tests/test_openspec_duplicate_check.py::test_real_repo_has_no_same_kind_heading_duplicate

### Requirement: the gate is wired where CI runs it

The duplication gate SHALL be reachable from `make openspec-duplicate-check`,
and `make openspec-check` SHALL depend on that target so `qa-validate`'s
OpenSpec gate executes the check on every PR (rule 6d/6f). The script uses
only the Python standard library, so it runs in the agent container's
python-env seam just as `openspec-tasks-check` does.

#### Scenario: the make target exists and the check is wired into openspec-check

- **Given** the repository `Makefile`
- **When** the openspec targets are read
- **Then** `openspec-duplicate-check` runs `scripts/openspec_duplicate_check.py`,
  `make openspec-check` lists `openspec-duplicate-check` in its dependencies,
  and `make test` runs the `test_openspec_duplicate_check` module

- **Test:** tests/test_openspec_duplicate_check.py::test_wired_into_make_openspec_check
