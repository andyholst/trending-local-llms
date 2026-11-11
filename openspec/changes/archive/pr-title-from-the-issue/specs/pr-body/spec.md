# pr-body

## ADDED Requirements

### Requirement: The PR title is composed from the issue's kind

`make pr-title ISSUE=<n> KIND=<data-gap|tech-debt>` MUST print a Conventional-Commit title naming
the issue and the kind of work, MUST refuse an unknown kind, and MUST be `@`-silenced so a capture
holds the title alone. The issue-bot PR step MUST call it instead of spelling a title inline.

#### Scenario: a tech-debt issue

- **Given** an issue labelled `tech-debt`
- **When** `make pr-title ISSUE=541 KIND=tech-debt` runs
- **Then** stdout is `fix(tech-debt): implement #541 …` and no command echo
- **Test:** tests/test_pr_body.py::test_the_pr_title_is_composed_from_the_issue_kind

#### Scenario: a data-gap issue

- **Given** an issue labelled `data-gap-analysis`
- **When** `make pr-title ISSUE=541 KIND=data-gap` runs
- **Then** stdout is `feat(data-gap): implement #541 …`
- **Test:** tests/test_pr_body.py::test_the_pr_title_is_composed_from_the_issue_kind

#### Scenario: an unknown kind is refused

- **Given** any other kind
- **When** the target runs
- **Then** it exits non-zero and names the choices, and the sweep is unchanged
- **Test:** tests/test_pr_body.py::test_the_pr_title_is_composed_from_the_issue_kind

#### Scenario: the workflow composes it

- **Given** the shipped "Open the PR" step
- **When** its text is read
- **Then** it calls `make pr-title` with a KIND derived from the issue's labels, and the inline
  title string is gone
- **Test:** tests/test_pr_body.py::test_the_pr_title_is_composed_from_the_issue_kind
