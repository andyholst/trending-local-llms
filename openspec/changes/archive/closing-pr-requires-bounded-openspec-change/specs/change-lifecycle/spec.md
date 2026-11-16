# change-lifecycle delta: closing-pr-requires-bounded-openspec-change

## ADDED Requirements

### Requirement: A closing implementation PR must carry a change that names each issue it closes

`make openspec-archive-check PR=<n>` reads the issues the pull request closes through `scripts/pr_closure.py`'s closing-keyword parser (one implementation, rule 6d) and requires each closed issue to be named by the `Issue:` line of at least one change — ACTIVE or ARCHIVED — in the PR head's tree, parsed with `openspec_index._refs` (the ONE proposal parser, rule 6d). A closed issue named by no change refuses the merge gate (exit 1) naming the issue and the remedy `make openspec-new NAME=…` (binding `Issue: #<n>`) or `make openspec-record-pr`; PRs whose head branch matches the keeper shape `ci/keeper-*` (#872) or the refresh shape `ci/trending-refresh-*` implement no issue and are exempt by shape.

#### Scenario: An implementation-shape PR closing an issue with no change is refused

Given a planted tree with NO change (active or archived) whose proposal names `Issue: #5001`
When the real `openspec_archive_check.py --pr 6001` runs with the stub `gh` answering the PR's title/body `closes #5001` and head branch `tech-debt-some-work-5001`
Then the exit is 1 and the output names issue #5001 and the `make openspec-new` remedy — the untracked implementation is caught before the squash, not after master loses the paper trail

- **Test:** tests/test_openspec_archive_check.py::test_a_closing_pr_with_no_openspec_change_is_refused

#### Scenario: An archived change naming the closed issue is the green shape

Given a planted tree whose `archive/` change names `Issue: #5001`
When the real script runs with `--pr 6001` against the same closing stub
Then the exit is 0 and the OK line reports the closing set — the change reached its full life before the merge

- **Test:** tests/test_openspec_archive_check.py::test_a_closing_pr_whose_issue_has_an_archived_change_passes

#### Scenario: Keeper and refresh shapes close nothing and owe no change

Given a PR whose `headRefName` is `ci/keeper-index-repair-20261117` (or `ci/trending-refresh-20261118-0003`)
When the real script runs with `--pr 6002` and the stub reports no closing keyword
Then the exit is 0 and the change-required prong is reported as exempt by shape — the same branch discrimination `make pr-closure` applies (rule 6e)

- **Test:** tests/test_openspec_archive_check.py::test_keeper_and_refresh_branches_are_exempt_from_the_change_required_prong

#### Scenario: A PR closing nothing owes nothing

Given a planted tree with an active change for an unrelated issue and a PR body carrying no closing keyword
When the real script runs with `--pr 6003` against an implementation-shape branch
Then the exit is 0 — the prong asserts only over issues the PR actually closes

- **Test:** tests/test_openspec_archive_check.py::test_a_pr_closing_nothing_owes_no_change
