# gh-json-fields-scope-boundary

## ADDED Requirements

### Requirement: The gh field contract states its projection-only boundary

`scripts/gh_json_fields.py` MUST state that it validates ONLY `--jq`/`-q` projections and that a
Python-side `.get()` field pick on ANY `gh api` answer is OUT OF SCOPE, naming the measured
32 read sites, the 18 unvalidated Python field reads and the 2 genuine exemptions. The
`api_jq_requests` docstring, the inline exemption comment and the `ARCHITECTURE.md` §6 row MUST
carry the same boundary. The module MUST expose `PYTHON_GET_FIELDS_OUT_OF_SCOPE = True` and
`UNVALIDATED_PYTHON_API_READ_SITES = 18`.

#### Scenario: the boundary is stated on the shipped module

- **Given** `scripts/gh_json_fields.py` at the landing head
- **When** a guard reads the module docstring, the `api_jq_requests` docstring and the constants
- **Then** the docstring carries `BOUNDARY (issue #1675): this contract validates ONLY `--jq`/`-q` projections`, the 32/18/2 counts are present, and both constants hold
- **Test:** tests/test_gh_json_fields.py::test_the_scope_claim_matches_the_tree

#### Scenario: the guard is RED on the base revision

- **Given** `git show origin/master:scripts/gh_json_fields.py` loaded as a module
- **When** the guard asserts the boundary
- **Then** it FAILS (neither constant exists and the unqualified claim is present) and the module exits 1
- **Test:** tests/test_gh_json_fields.py::test_the_scope_claim_matches_the_tree

#### Scenario: the scan stays silent on Python picks (non-vacuous)

- **Given** a scratch tree whose only `gh api` call picks a field in Python
- **When** `scan_scripts` runs over that tree
- **Then** it is GREEN (0 findings), proving the narrowed claim is TRUE rather than merely reworded
- **Test:** tests/test_gh_json_fields.py::test_the_scope_claim_matches_the_tree

#### Scenario: no scan behaviour change on the shipped tree

- **Given** the shipped repository tree
- **When** `--scan` runs
- **Then** it exits 0 with 0 findings, discovering 31 `gh api` token-lists (17 projecting, 14 not) and 5 identity `.[]` projections
- **Test:** tests/test_gh_json_fields.py::test_the_scope_claim_matches_the_tree
