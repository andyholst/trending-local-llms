# code-review-scan

## ADDED Requirements

### Requirement: the secrets check runs without a credential

`make code-review-scan` SHALL run its `secrets-not-defined` check unconditionally, against the
repository's own declared secret contract, and SHALL NOT gate that check on any read that needs a
token with admin on the repository. A live `gh secret list` read SHALL only add names to the
contract, never replace or disable it.

#### Scenario: an undeclared secret is reported with no API read

- **GIVEN** a workflow reading `secrets.NOT_A_SECRET`, which the contract does not declare
- **WHEN** the deterministic checks run with no live secret list at all (the production shape:
  the default token is refused with `HTTP 403`)
- **THEN** `secrets-not-defined/NOT_A_SECRET` IS reported, and the evidence names the contract
  rather than `gh secret list`

- **Test:** `tests/test_code_review.py::test_a_secret_outside_the_contract_is_reported_with_no_api`

#### Scenario: a declared secret and GITHUB_TOKEN are never reported

- **GIVEN** a workflow reading a secret the contract declares, and another reading `GITHUB_TOKEN`
- **WHEN** the checks run
- **THEN** neither is reported

- **Test:** `tests/test_code_review.py::test_a_contract_secret_is_not_reported`

### Requirement: the contract matches what the workflows read

`DECLARED_SECRETS` SHALL equal the set of `secrets.` references across the repository's workflows,
in both directions, so it cannot decay into a hand-maintained allowlist: adding a reference forces
a declaration, and declaring a name nothing reads fails.

#### Scenario: the two sets agree exactly

- **GIVEN** this repository's workflows and its declared contract
- **WHEN** the referenced names and the declared names are compared
- **THEN** there is no referenced-but-undeclared name and no declared-but-unread name

- **Test:** `tests/test_code_review.py::test_the_declared_secret_contract_matches_what_the_workflows_read`

### Requirement: a commented reference is not a read

The scan SHALL ignore `secrets.` references inside `#` comments, so a documentation example is
prose and not a finding about the repository's own comment.

#### Scenario: a doc comment is not a finding

- **GIVEN** `.github/workflows/qa-validate.yml:144`, which documents the guard with a literal
  `${{ secrets.X }}` in a comment
- **WHEN** the checks run over this repository
- **THEN** no finding is reported for `X`

- **Test:** `tests/test_code_review.py::test_a_commented_reference_is_not_a_read`
