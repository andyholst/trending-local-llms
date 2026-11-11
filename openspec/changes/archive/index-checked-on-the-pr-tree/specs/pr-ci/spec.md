# pr-ci

## ADDED Requirements

### Requirement: The PR gate is verified against the PR's own tree

`qa-validate`'s `validate` job MUST check out the pull request's head SHA, falling back to
`github.sha` on a push, with full history.

#### Scenario: a pull request

- **Given** a `pull_request` run
- **When** the checkout step executes
- **Then** `ref` resolves to the PR's head SHA, so a generated file is compared with the tree that produced it
- **Test:** tests/test_workflows.py::test_the_validate_job_checks_out_the_pr_tree_not_the_merge_result

#### Scenario: a push to master

- **Given** a `push` run
- **When** the checkout step executes
- **Then** `ref` falls back to `github.sha` (the merge result), so master's index is still verified
- **Test:** tests/test_workflows.py::test_the_validate_job_checks_out_the_pr_tree_not_the_merge_result
