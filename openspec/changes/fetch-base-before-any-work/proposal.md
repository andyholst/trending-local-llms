# Proposal: fetch-base-before-any-work

Issue: #440 (filed first, with the rule-3c declaration)

## Why

`AGENTS.md` §6n requires a worktree cut from the **freshly fetched** `refs/remotes/origin/master`
(`make worktree-new`) and has CI assert its own checkout (`make base-check`). It says nothing
about **every other kind of work** — a tech-debt review, a store read, an analysis pass, an edit
in the user's own checkout — all of which run against whatever `master` the clone happens to hold.

Measured in this repo: a review of the open tech-debt issues, a README inspection and several
"is this still true against latest main?" passes were done on a base that had quietly moved, and
the only thing that caught it was a human asking. The worktree seam fetches by construction;
everything else relies on the author remembering.

## What Changes

- **`AGENTS.md` §6n gains the always-fetch half**: *Before ANY work — one fetch, always.*
  `git fetch origin` and, in a checkout you own, `git pull --ff-only`; a worktree is cut from the
  fetched base by construction and in a checkout you own the same assertion is `make base-check`
  (its `--in-place` shape); every other run **states the base SHA it read**, because a stale base
  is a conclusion about code that has already moved.
- **`§8`'s `tests/test_worktree_base.py` row** now names that failure among what the guard catches.
- **The guard pins the wording** (`tests/test_worktree_base.py::test_the_rulebook_states_the_rule`):
  a fetch before any work, the fast-forward pull, the stated base SHA, and the machinery
  (`make base-check`). Removing the rule fails the suite.

Verified RED against the pre-change `AGENTS.md` (3 failures) and GREEN after (`PASSED 63 | FAILED 0`).

## Impact

`AGENTS.md` (§6n bullet + §8 row), `tests/test_worktree_base.py` (4 new assertions), this OpenSpec
change and the regenerated `OPENSPEC.md`. **No code, target, stage, job or image changes** — the
rule is about how work STARTS, and the machinery it names (`make worktree-new`, `make base-check`)
already exists and is already wired.

## Rule 3c — review-required

This changes AGENTS.md's behaviour, so the AGENTS.md diff and the guard that pins it need a
reviewer's sign-off before the merge; the issue (#440) carries the same declaration.

## Not covered

- **A new stage or target.** Nothing mechanical is missing: `make worktree-new` fetches, and
  `make base-check --in-place` proves a checkout is the fetched tip. The gap was the RULE.
- **Auto-fetching inside a run.** Silently moving an author's checkout under them is the opposite
  of rule 6n's "never edit the user's checkout"; the rule asks for an explicit fetch and a stated
  base instead.
