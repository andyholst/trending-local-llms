# auto-merge

## ADDED Requirements

### Requirement: Auto-merge rebases a behind-and-clean bot branch and regenerates its index before the squash

qa-validate's `auto-merge` job MUST run `make auto-merge-rebase` BEFORE its squash-merge step.
The seam reads the PR through `gh pr view --json` and classifies it against the FETCHED
`origin/master` through ONE pure verdict function: `not-open`, `draft`, `conflicting`,
`human-owned`, `refs-unreadable`, `current`, `behind-and-clean-bot`. A branch is
`behind-and-clean-bot` only when it carries a bot-owned prefix (`ci/`, `tech-debt-`,
`data-gap-`, `issue-`), is BEHIND the fetched base, and is GitHub-mergeable (not
CONFLICTING/DIRTY). For such a branch the job MUST rebase it onto the fetched master,
REGENERATE `OPENSPEC.md` on the rebased tree through the ONE generator
(`scripts/openspec_index.py --write`), commit the regenerated file as the agent identity, and
push with `--force-with-lease` pinned to the fetched remote tip. The step MUST print
`verdict=` and `rebased=true|false`. A rebase that git CONFLICTS on MUST abort and leave the
remote branch byte-identical.

#### Scenario: a behind-and-clean bot branch is rebased and its index is current on the rebased tree

- **Given** a real git fixture: a bot branch `ci/data-gap-77-x` branched from `master`, and `master` moved since (an OpenSpec change was ARCHIVED on `master`) so the branch's committed `OPENSPEC.md` lacks the archive, with a stub `gh` answering the PR `MERGEABLE`/`BEHIND`
- **When** `python3 scripts/auto_merge_rebase.py --pr 77 --repo o/r` runs against the fixture checkout
- **Then** the run prints `rebased=true`; the remote branch head moved; `OPENSPEC.md` on the new head lists the archive; `scripts/openspec_index.py --check` is GREEN on the new head; the remote head carries the index-regeneration commit
- **Test:** `tests/test_auto_merge_rebase.py::test_behind_clean_bot_branch_is_rebased_with_a_current_index`

#### Scenario: a head that already carries the fetched base merges as today

- **Given** the same fixture where `master` has NOT moved (the bot branch is at/ahead of the fetched base)
- **When** the seam runs
- **Then** it prints `verdict=current` and `rebased=false`, pushes nothing, and the remote branch head is byte-identical
- **Test:** `tests/test_auto_merge_rebase.py::test_current_head_reports_current_and_pushes_nothing`

#### Scenario: a human-owned behind branch is reported and never rewritten

- **Given** the fixture with a behind branch `andy/human-feature` and a stub `gh` PR for it
- **When** the seam runs
- **Then** it prints `verdict=human-owned` and `rebased=false` with a report line naming the branch, and the remote branch head is byte-identical
- **Test:** `tests/test_auto_merge_rebase.py::test_human_owned_behind_branch_is_reported_and_untouched`

#### Scenario: a conflicting branch aborts the rebase and stays byte-identical

- **Given** two fixture shapes: (a) a stub `gh` PR GitHub reports CONFLICTING (a human edited the same file as `master` differently); (b) a bot PR GitHub calls CLEAN where the git rebase itself conflicts
- **When** the seam runs on either shape
- **Then** shape (a) prints `verdict=conflicting` without touching git refs; shape (b) aborts the rebase, prints `verdict=kept` and `rebased=false`, and the remote branch head is byte-identical in both
- **Test:** `tests/test_auto_merge_rebase.py::test_conflicting_branches_are_never_rewritten`

### Requirement: The squash gate honors rebased=true — the stale event head is never squashed

After a landed rebase the run's event head no longer matches the branch, so the squash-merge
step MUST be skipped: its `if:` MUST carry
`steps.auto-merge-rebase.outputs.rebased != 'true'` alongside the do-not-merge hold gate, and
the rebase step MUST sit BEFORE the squash step in the `auto-merge` job and call
`make auto-merge-rebase` (rule 6m). A wiring guard MUST refuse any `auto-merge` job without
the rebase step before the squash, and any squash `if:` that does not honor `rebased=true` —
including the pre-#1049 merge-as-is workflow read from `origin/master`.

#### Scenario: the wiring refuses the merge-as-is flow (the old behavior is red)

- **Given** the `auto-merge` job with the rebase step removed, or the squash `if:` restored to its pre-#1049 form (the exact text `git show origin/master:.github/workflows/qa-validate.yml` carries)
- **When** the wiring guard checks the job
- **Then** it fails, naming the missing step-order and/or the missing `rebased` gate
- **Test:** `tests/test_auto_merge_rebase.py::test_the_auto_merge_wiring_refuses_the_merge_as_is_flow`

#### Scenario: the shipped workflow carries the gate in the right order

- **Given** `.github/workflows/qa-validate.yml`'s `auto-merge` job
- **When** the workflow tests read its steps
- **Then** the `#1049` rebase step (id `auto-merge-rebase`, calling `make auto-merge-rebase`) precedes the squash step, and the squash `if:` keys on `steps.auto-merge-rebase.outputs.rebased != 'true'` beside the hold gate
- **Test:** `tests/test_workflows.py::test_auto_merge`

### Requirement: The shared rebaser regenerates the index on every rebased tree

`scripts/pr_health.py`'s `rebase_and_push` — the ONE rebaser used by the §6s `make pr-health
REBASE=1` sweep and by `scripts/auto_merge_rebase.py` — MUST regenerate `OPENSPEC.md` on the
rebased tree through the ONE generator and commit it as the agent BEFORE the lease push, so a
branch the sweep rebases also carries a merge-time-current index. A failed regeneration MUST
stop the push (the remote branch stays untouched).

#### Scenario: the sweep's rebase lands a regenerated index commit

- **Given** the `tests/test_pr_health.py` real-git rebase fixture: a behind-and-clean bot branch, `master` moved, and an `openspec/` tree whose committed `OPENSPEC.md` predates the move
- **When** the sweep runs with `REBASE=1`
- **Then** the pushed head carries an `OPENSPEC.md` regenerated on the rebased tree (the index check passes on it) and the rebase note names the regeneration
- **Test:** `tests/test_pr_health.py::test_the_rebaser_regenerates_the_index_on_the_rebased_tree`

#### Scenario: a failed regeneration never pushes a half-repaired branch

- **Given** the `auto_merge_rebase` seam whose shared rebaser reports a regeneration failure
- **When** the seam finishes
- **Then** it prints `verdict=kept` and `rebased=false`, and the remote branch head is byte-identical
- **Test:** `tests/test_auto_merge_rebase.py::test_regeneration_failure_keeps_the_branch_untouched`
