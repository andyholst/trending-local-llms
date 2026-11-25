## ADDED Requirements

### Requirement: A failing `gh` names the credential VARIABLE in use

`scripts/verify_closure.py` SHALL name the credential variable the process is using —
`GH_TOKEN` when it is set, else the default `GITHUB_TOKEN` — in the refusal raised when `gh`
exits non-zero. The refusal SHALL carry the variable NAME only, never its value (rule 3d).

#### Scenario: GH_TOKEN is set

- **Given** a process whose environment sets `GH_TOKEN`
- **When** `gh` exits 1 with `HTTP 401: Bad credentials`
- **Then** the refusal labels and names `GH_TOKEN`, does not name `GITHUB_TOKEN`, and prints no token value
- **Test:** tests/test_verify_closure.py::test_a_gh_failure_names_the_credential_variable_in_use

#### Scenario: Only the default token exists

- **Given** a process whose environment sets neither credential variable
- **When** `gh` exits 1
- **Then** the refusal names the default `GITHUB_TOKEN` and invents no `GH_TOKEN`
- **Test:** tests/test_verify_closure.py::test_a_gh_failure_names_the_credential_variable_in_use

### Requirement: The guard is RED on the pre-change refusal

The suite SHALL run `origin/master`'s own `scripts/verify_closure.py` against the same stub
`gh`, so the new assertion fails on the revision that carries no credential name and passes
only once the refusal names the variable.

#### Scenario: The base revision's refusal

- **Given** `git show origin/master:scripts/verify_closure.py` resolves
- **When** that revision runs against a stub `gh` that exits 1
- **Then** the guard requires the credential marker in its stderr — RED before the merge, GREEN after
- **Test:** tests/test_verify_closure.py::test_origin_masters_refusal_carries_no_credential_marker
