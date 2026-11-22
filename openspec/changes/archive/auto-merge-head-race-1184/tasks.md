# Tasks: auto-merge-head-race-1184

- [x] Verify part 2 of #1184 (`action_required` ghost detection) is already landed by the #1115 fix — do not re-implement
- [x] Add `scripts/auto_merge_head_check.py` with the pure `head_verdict` and a fail-closed `head_moved` output
- [x] Add the `auto-merge-head-check` Makefile target + internal recipe
- [x] Add the `head-check` step to qa-validate's `auto-merge` job and gate the squash on `moved != true`
- [x] Add `tests/test_auto_merge_head_check.py` (22 checks, RED on `origin/master`: 8 failures)
- [x] Prove the fail-closed unreadable-head case (bug found by the test and fixed)
- [x] Update ARCHITECTURE.md for the new script/target and regenerate the generated block
- [x] Regenerate OPENSPEC.md and pass lint/openspec/architecture/findings gates
- [~] Add the AGENTS.md §8 regression-guard row — blocked: rule 3c human sign-off (AGENTS.md protected in a headless leg; owed row declared in findings.md)
- [~] Record the PR against this change (`make openspec-record-pr`) — blocked: PR number is assigned only after `gh pr create`, and recording archives this change in the same amend
