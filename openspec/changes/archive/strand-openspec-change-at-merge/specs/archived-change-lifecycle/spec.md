## ADDED Requirements

### Requirement: a closing pull request lands its own change archived

When `make openspec-archive-check PR=<n>` validates a pull request, any ACTIVE
change whose `Issue:` is one of that PR's closing issues SHALL fail the check
whether or not the change names a `PR:` line — the exemption that let a
recorded-but-unarchived change merge (issue #866) is removed. The validated
head passes only when the change is ARCHIVED on the branch that merges
(`make openspec-record-pr ISSUE=<issue> PR=<pr>` records AND archives), so a
merged-but-active change cannot survive a pipeline cycle.

#### Scenario: a recorded-but-unarchived closing change is red

- **Given** a fixture tree with an ACTIVE change whose proposal names
  `Issue: #768` and already records `PR: #781`
- **When** the check runs with `--pr 781` and the stub `gh` reports that PR's
  body as `Closes #768`
- **Then** the check exits 1 naming the change, the issue, the PR, and the
  remedy (`make openspec-record-pr ISSUE=768 PR=781` records and archives)
- **Test:** tests/test_openspec_archive_check.py::test_the_closing_pr_prong_fails_a_recorded_but_unarchived_change

#### Scenario: the closing head passes once its own change is archived

- **Given** a fixture tree where the change whose issue the PR closes lives in
  `openspec/changes/archive/` (the recorded-and-archived shape)
- **When** the check runs with `--pr 781` against a PR whose body closes that
  issue
- **Then** the check exits 0 and reports the closing set on its OK line
- **Test:** tests/test_openspec_archive_check.py::test_the_closing_pr_prong_passes_when_the_change_is_archived_by_the_pr

#### Scenario: an active unrecorded closing change is still red (the #779 half)

- **Given** a fixture tree with an active change whose proposal references
  `Issue: #768` and names no `PR:`
- **When** the check runs with `--pr 781` and the stub `gh` reports that PR's
  body as `Closes #768`
- **Then** the check exits 1 naming the change, the issue, the PR, and the fix
  (`make openspec-record-pr ISSUE=768 PR=781`)
- **Test:** tests/test_openspec_archive_check.py::test_the_closing_pr_prong_fails_an_active_change_it_would_strand

#### Scenario: a change the PR does not close is not flagged

- **Given** the fixture tree where the PR closes #999 while the active change
  references `Issue: #768` (open)
- **When** the check runs with `--pr 781`
- **Then** the check exits 0 for that change (archiving a change this PR does
  not close remains a different, #812-governed question)
- **Test:** tests/test_openspec_archive_check.py::test_the_closing_pr_prong_ignores_changes_the_pr_does_not_close
