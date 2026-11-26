# filers-label-rest-1766

## ADDED Requirements

### Requirement: The issue filers apply labels through the REST endpoint

The data-gap-analysis, file-findings, issue-review and issue-verdict filers SHALL
apply labels with the REST endpoint (`gh api repos/<repo>/issues/<n>/labels`)
instead of the GraphQL `addLabelsToLabelable` mutation, so a PAT-shaped credential
that can create an issue but not label one still files the issue and moves the
queue forward.

#### Scenario: a label write reaches REST for every filer

- **Given** a filed issue whose label application would otherwise use
  `addLabelsToLabelable`
- **When** a filer writes the issue's label
- **Then** the label is sent to `repos/<repo>/issues/<n>/labels` over REST
- **Test:** tests/...::test_filers_apply_labels_via_rest

### Requirement: the GraphQL label mutation is never attempted on a PAT-shaped credential

Each filer module carries a stub-gh guard that refuses the GraphQL `addLabelsToLabelable`
path when the token is the repository's PAT; the guard exits non-zero and the
REST path is used instead. No stub-gh guard may allow a fallback to GraphQL.

#### Scenario: a PAT-shaped credential reaches the guard

- **Given** a filers' token that cannot call `addLabelsToLabelable`
- **When** the filer attempts its label write
- **Then** the guard refuses the GraphQL path and the REST path is used
- **Test:** tests/...::test_stub_gh_guard_refuses_graphql_on_pat
