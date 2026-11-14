# pr-sweep-rebase

## ADDED Requirements

### Requirement: The sweep rebases behind-and-clean bot PR branches and never rewrites anything else

`make pr-health REBASE=1` (run by the weekly `pr-health.yml` sweep) fetches
every branch tip, and for each OPEN non-draft PR whose head branch is one of
the bot/agent shapes (`ci/…`, `tech-debt-…`, `data-gap-…`, `issue-…`): if the
branch does not carry
`origin/master` as an ancestor, it is rebased onto `origin/master` in a scratch
worktree and pushed back to the PR's own head with `--force-with-lease` pinned
to the fetched remote tip. A CONFLICTING PR, a human-owned branch (any other
prefix), a draft, and the base branch itself are NEVER rewritten. A failed
rebase aborts and leaves the branch byte-identical. The silent-PR verdict and
exit contract are unchanged.

#### Scenario: a behind-and-clean ci/ branch is rebased with its own commit intact

- **Given** a real local origin whose `master` moved ahead of a clean
  `ci/data-gap-7-x` PR head, with the PR read through the stubbed `gh`
- **When** `scripts/pr_health.py --rebase --dir <clone>` runs
- **Then** the run prints `rebaser #7 … REBASED`, the remote branch now carries
  `origin/master` as an ancestor, and the branch's own commit survives
- **Test:** tests/test_pr_health.py::test_a_behind_clean_bot_branch_is_rebased_and_pushed_and_a_human_branch_is_never_rewritten

#### Scenario: a human-owned branch and a CONFLICTING bot branch are never rewritten

- **Given** the same planted tree plus a behind `fix/human-behind` branch and a
  `CONFLICTING` `ci/clash-8-y` branch
- **When** the rebaser runs
- **Then** both remote branch OIDs are byte-identical afterwards and the plan
  classifies them `human-branch` / `conflict`
- **Test:** tests/test_pr_health.py::test_a_behind_clean_bot_branch_is_rebased_and_pushed_and_a_human_branch_is_never_rewritten

#### Scenario: the plan classifies by ownership, conflict and draft before any git runs

- **Given** an open-PR list mixing `ci/`, human-prefixed, CONFLICTING and draft entries
- **When** `rebase_plan()` runs
- **Then** only clean `ci/` entries are `rebase-if-behind`; drafts appear in no plan row
- **Test:** tests/test_pr_health.py::test_rebase_plan_classifies_by_ownership_and_conflict

#### Scenario: the sweep workflow and the Makefile carry the rebaser half

- **Given** the shipped `pr-health.yml` and `Makefile`
- **When** the wiring assertions run
- **Then** the sweep step calls `make pr-health … REBASE=1`, the sweep job has
  `contents: write`, its checkout has `fetch-depth: 0`, and the Makefile
  forwards `REBASE` to `--rebase`
- **Test:** tests/test_pr_health.py::test_the_sweep_is_wired_to_a_target_a_workflow_and_a_guard
