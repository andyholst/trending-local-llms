## ADDED Requirements

### Requirement: auto-merge lands a merge commit carrying the merged PR's own message

qa-validate's `auto-merge` job MUST squash-merge the validated head commit with the merged PR's own TITLE as the commit subject and the merged PR's BODY as the commit body, so the commit that lands on master satisfies the message pattern's own gates (the five sections and the bound closing keyword, #771). A merge that lands only the PR title MUST fail the pipeline guard.

#### Scenario: a validated green PR is squash-merged with its full message

- **Given** `validate` and `live-smoke` are green on the exact head commit, the PR is OPEN and carries no `do-not-merge` label
- **When** the `auto-merge` job merges
- **Then** it reads the merged PR's title and body first (`gh pr view --json title` / `--json body`) and merges with `--subject <title>`, `--body-file <body>`, `--match-head-commit <validated sha>` and `--delete-branch`, and master's `make commit-message-check` accepts the landed squash commit
- **Test:** tests/test_workflows.py::test_auto_merge

#### Scenario: a title-only merge fails the guard

- **Given** the merge step drops `--subject` or `--body-file`, or never reads the merged PR's title and body
- **When** `make test` runs
- **Then** `test_auto_merge` MUST fail (the guard is RED on the pre-fix step)
- **Test:** tests/test_workflows.py::test_auto_merge
