# openspec-lifecycle

## ADDED Requirements

### Requirement: every active change names the issue its completing PR closes

An active change's proposal SHALL carry an `Issue:` line with the number of the issue the change completes, so the lifecycle guard (`scripts/openspec_archive_check.py --pr <n>`) can match the closing PR to the change that implements it (rule 6f; issues #518/#779/#1109).

#### Scenario: the new change binds Issue: #1773

- **Given** the change `openspec/changes/wiki-rulebook-1773/proposal.md` with `Issue: #1773` and `PR: fix/wiki-rulebook-1773`
- **When** `make openspec-check` runs on PR #1774's tree (index current + archive-check with --pr 1774)
- **Then** the index lists the change as active, `openspec-index-check` passes, and no closed issue that PR closes is named by no change

- **Test:** tests/test_openspec_index.py (regeneration of the index rows) and tests/test_openspec_archive_check.py (the guard's closing-PR prong)
