# fix-bot-repair-loop

## ADDED Requirements

### Requirement: A bot PR that cannot merge is dispatched to the repair bot

The silent-PR sweep MUST dispatch `fix-bot` for a silent pull request whose head branch is a
`ci/…` branch, capped at a configured number of `fix-bot:` commits per pull request, and MUST
NOT dispatch for any other branch.

#### Scenario: a conflicting bot PR

- **Given** a silent open PR on `ci/trending-refresh-<UTC>`
- **When** the sweep runs with `--repair`
- **Then** `fix-bot` is dispatched with that PR number and branch, unless the cap is already reached
- **Test:** tests/test_pr_health.py::test_only_a_bot_branch_is_repaired_and_the_cap_holds

#### Scenario: a human's branch

- **Given** a silent open PR on `fix/hardware-is-not-an-engine`
- **When** the sweep runs with `--repair`
- **Then** it is reported and NOT dispatched, because the loop would push to someone else's branch
- **Test:** tests/test_pr_health.py::test_only_a_bot_branch_is_repaired_and_the_cap_holds

### Requirement: A conflicted base merge is a repair, not an abort

`scripts/fix_loop.sh` MUST keep a conflicted base merge, put the conflicted paths and their hunks
into the report the Hermes round reads, treat the branch as RED while the index is unmerged,
complete the merge when the index comes back clean, and `--abort` it if the last round could not
resolve it.

#### Scenario: the base moved onto the same line

- **Given** a branch and a base that both edited the same file
- **When** the loop runs its base merge
- **Then** the conflict is named in the log, the report carries the hunks and the
  "regenerated, never hand-merged" rule, a Hermes round runs, and after the last round the merge
  is aborted with the branch's own commit untouched
- **Test:** tests/test_fix_loop.py::test_a_conflicting_base_merge_is_handed_to_a_round_and_aborted_if_hopeless
