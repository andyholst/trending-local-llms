# pipeline-failure-filer

## ADDED Requirements

### Requirement: The label fallback survives a host PAT that cannot call GraphQL

When a filing host is authenticated with a credential that refuses the GraphQL `addLabelsToLabelable` mutation, the failure filer SHALL still apply the `tech-debt` label and append the ledger row in the same pass. The fallback SHALL use the REST label endpoint (`gh api -X POST repos/<repo>/issues/<n>/labels`), never `gh issue edit --add-label`. The normal path SHALL remain byte-identical for the CI default token.

#### Scenario: The owner PAT refuses GraphQL but the issue still lands labelled

- **Given** a host whose `gh` refuses `gh issue edit --add-label` with `addLabelsToLabelable`, and `gh issue create --label` applied nothing (#161)
- **When** the filer files a concluded-bad run
- **Then** it applies `tech-debt` through the REST endpoint, exits 0, and appends the ledger row — never attempting the GraphQL mutation
- **Test:** tests/test_pipeline_failure_issue.py::test_the_label_fallback_uses_rest_when_the_pat_refuses_graphql

#### Scenario: A normal filing leaves an already-labelled issue alone

- **Given** the label is already present on the created issue (the CI default-token path)
- **When** the filer files the run
- **Then** no fallback write is issued and the existing filing, scrubbed error block and ledger shape are unchanged
- **Test:** tests/test_pipeline_failure_issue.py::test_filing_diagnoses_every_failure_with_the_log_error_block
