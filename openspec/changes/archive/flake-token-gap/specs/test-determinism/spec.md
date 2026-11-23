## ADDED Requirements

### Requirement: A credential the tree does not own is declared, not asserted

The module SHALL treat "this identity can resolve a GitHub token" as an environmental
precondition: when no token resolves it SHALL announce a declared coverage gap naming the
guard and the reason, and SHALL NOT fail. The tree-owned halves SHALL stay hard checks.

#### Scenario: No token resolves on this identity

- **Given** an identity where `gh auth token` is absent or fails and no `GH_TOKEN`/`GITHUB_TOKEN` is set
- **When** the module runs
- **Then** it announces one `[coverage-gap]` line and still passes
- **Test:** tests/test_refusals_land_declaration.py::test_the_scratch_subprocesses_inherit_authentication

#### Scenario: A token resolves

- **Given** an identity with a resolvable token
- **When** the module runs
- **Then** the token is passed to the scratch subprocesses BY NAME and never printed
- **Test:** tests/test_refusals_land_declaration.py::test_the_scratch_subprocesses_inherit_authentication

### Requirement: A sibling's pass/fail half is hard only when its probe can authenticate

`test_the_measured_suite_modules_leave_the_tree_clean` SHALL run the three sibling modules and
require their exit 0 ONLY when the identity resolved a token; otherwise it SHALL announce a
declared gap naming the siblings. The tree-clean assertion SHALL stay hard in both cases.

#### Scenario: A sibling reddens only because its probe is unauthenticated

- **Given** an identity with no resolvable token
- **When** the three siblings run
- **Then** the module announces the gap and passes, and the tree-clean half is still asserted
- **Test:** tests/test_refusals_land_declaration.py::test_the_measured_suite_modules_leave_the_tree_clean

#### Scenario: A sibling is genuinely broken

- **Given** an identity with a resolvable token
- **When** a sibling exits non-zero
- **Then** the module FAILS naming that sibling
- **Test:** tests/test_refusals_land_declaration.py::test_the_measured_suite_modules_leave_the_tree_clean
