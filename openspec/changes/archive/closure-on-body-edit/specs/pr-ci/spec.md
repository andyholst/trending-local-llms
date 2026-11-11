# pr-ci

## ADDED Requirements

### Requirement: The closure check re-runs when the PR body is edited

A pipeline MUST run `make pr-closure` on `pull_request` events that include `edited`, so a body
that gains or loses its closing keyword is re-checked without a new commit.

#### Scenario: the trigger

- **Given** `.github/workflows/pr-closure.yml`
- **When** the guard reads its `on:` block
- **Then** the `pull_request` types include `edited`, `opened`, `synchronize` and `reopened`
- **Test:** tests/test_workflows.py::test_the_closure_check_reruns_when_the_pr_body_is_edited

#### Scenario: the job

- **Given** the workflow's `closure` job
- **When** the guard reads its steps
- **Then** it checks the repository out, runs `make pr-closure`, and `needs: guard`
- **Test:** tests/test_workflows.py::test_the_closure_check_reruns_when_the_pr_body_is_edited

#### Scenario: the pipeline is read-only

- **Given** the whole workflow document
- **When** the guard scans it
- **Then** it contains no `git push`, no `gh pr merge`, no `gh pr comment` and no `--admin`
- **Test:** tests/test_workflows.py::test_the_closure_check_reruns_when_the_pr_body_is_edited

### Requirement: qa-validate keeps its own closure gate

Adding a trigger MUST NOT remove the closure check from `qa-validate`'s `validate` job.

#### Scenario: the existing gate

- **Given** `qa-validate.yml`
- **When** the guard reads the `validate` job's steps
- **Then** `make pr-closure` is still among them
- **Test:** tests/test_workflows.py::test_the_closure_check_reruns_when_the_pr_body_is_edited
