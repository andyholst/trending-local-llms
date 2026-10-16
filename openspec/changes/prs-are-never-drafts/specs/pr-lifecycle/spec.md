# pr-lifecycle

## ADDED Requirements

### Requirement: A run opens a reviewable PR, never a draft

Every PR a pipeline opens (the implementer's implementation PR, the refresh's data PR) MUST be
created ready for review. A draft is excluded by `qa-validate`'s `auto-merge` gate, so a draft run
ends with a change that no job can ever land, while the run itself reports success — the failure is
silent and terminal. Holding a change for review is the reviewable PR plus GitHub's required checks,
never a draft flag.

WHEN a pipeline opens a PR,
THEN it is created without `--draft`, so the merge gate can run once `validate` and `live-smoke` are
green.

#### Scenario: no workflow opens a draft PR

- **Given** every `.github/workflows/*.yml` in the repository
- **When** the workflow test scans each `gh pr create` invocation
- **Then** none of them passes `--draft`, because the merge gate skips a draft for ever
- **Test:** `tests/test_workflows.py::test_no_pipeline_opens_a_draft_pr`

#### Scenario: the implementer's PR is created ready for review

- **Given** `issue-bot.yml`'s PR-opening step
- **When** it is inspected
- **Then** it creates the PR against `master` with the owner PAT and no `--draft`, so CI runs and
  `auto-merge` can land it when green
- **Test:** `tests/test_workflows.py::test_no_pipeline_opens_a_draft_pr`

#### Scenario: the merge gate still refuses a draft

- **Given** `qa-validate.yml`'s `auto-merge` job
- **When** its `if:` condition is inspected
- **Then** it requires `github.event.pull_request.draft == false`, so a draft cannot be merged even
  if one is somehow created by hand
- **Test:** `tests/test_workflows.py::test_auto_merge`
