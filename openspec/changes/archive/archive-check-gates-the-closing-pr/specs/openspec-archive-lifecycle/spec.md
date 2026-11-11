## ADDED Requirements

### Requirement: the closing pull request gates every active change it would strand

When `make openspec-archive-check PR=<n>` validates a pull request, the check
SHALL read that PR's closing issues (through `scripts/pr_closure.py`'s closing
parser, the one implementation) and fail while any ACTIVE change references
one of those issues with `Issue:` and does not name this PR on its `PR:` line.
The merge that closes the change's issue must land the change archived (or
explicitly recorded with this PR); an unarchived change must never reach
`master` behind the PR that closed its issue.

#### Scenario: a PR closing the issue of an active unrecorded change is red

- **Given** a fixture tree with an active change whose proposal references
  `Issue: #768` and names no `PR:`
- **When** the check runs with `--pr 781` and the stub `gh` reports that PR's
  body as `Closes #768`
- **Then** the check exits 1 naming the change, the issue, the PR, and the fix
  (`make openspec-record-pr ISSUE=768 PR=781`)
- **Test:** tests/test_openspec_archive_check.py::test_the_closing_pr_prong_fails_an_active_change_it_would_strand

#### Scenario: the same change passes once it names the validating PR

- **Given** the same fixture tree, with the change's proposal recording
  `PR: #781` while the PR is still unmerged
- **When** the check runs with `--pr 781`
- **Then** the check exits 0 (the recorded head is green; the merged-PR prong
  decides after merge)
- **Test:** tests/test_openspec_archive_check.py::test_the_closing_pr_prong_passes_when_the_change_names_that_pr

#### Scenario: a change unrelated to the PR's closing issues is not flagged

- **Given** the fixture tree where the PR closes #999 while the active change
  references `Issue: #768` (open)
- **When** the check runs with `--pr 781`
- **Then** the check exits 0 for that change
- **Test:** tests/test_openspec_archive_check.py::test_the_closing_pr_prong_ignores_changes_the_pr_does_not_close

#### Scenario: a PR whose state cannot be read fails loudly

- **Given** the stub `gh` that refuses the PR lookup
- **When** the check runs with `--pr 781`
- **Then** the check exits 2 naming what could not be read (never a clean
  report from a scan that could not see)
- **Test:** tests/test_openspec_archive_check.py::test_an_unreadable_closing_pr_is_loud

### Requirement: qa-validate passes the pull request number to the lifecycle check

The `validate` job's OpenSpec lifecycle step SHALL invoke
`make openspec-archive-check` with the pull request number on `pull_request`
events (and without it otherwise), so the closing-PR prong runs on every PR
before any merge.

#### Scenario: the workflow forwards the PR number

- **Given** `.github/workflows/qa-validate.yml` on this branch
- **When** its lifecycle step is read
- **Then** it calls `make openspec-archive-check` with the event's PR number
  and `make openspec-archive-check` forwards `PR=` to `--pr`
- **Test:** tests/test_openspec_archive_check.py::test_the_workflow_passes_the_pull_request_number
