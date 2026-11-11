# Proposal: adopt-then-rebase-the-base

Issue: #500 (measured: run 39548077538 discarded a finished implementation because `master` moved
while the agent worked)

## Why

The implementer asserted its base **twice**: correctly at step 4 (`Assert the base is the freshly
fetched origin/master`), then again at step 11, where it created the branch with
`make worktree-new BRANCH=… IN_PLACE=1` — and `worktree-new` refuses when `HEAD != fetched tip`.
Between the two assertions it spent ~25 minutes implementing, and one merge landed (`#499`).
Result: `REFUSED: STALE: … HEAD 08a8bf3 (1 commit behind)` → `make: *** Error 1` → no commit, no
push, no PR, and not even the patch artifact (that path was gated on the workflow-scope rejection).
Issue #177's implementation was thrown away after being finished.

`base-check`'s refusal is right where the tree carries no work and wrong where it carries the
agent's edits — the same distinction #448 drew for `aggregate` (which `base-advance` fixed, because
that job had written nothing).

## What Changes

- **`scripts/worktree_base.py` gains `adopt`**: cut the branch from the CURRENT `HEAD` (carrying the
  agent's uncommitted edits), or attach the branch if it already exists (a re-run) — **without**
  re-asserting the base, reporting `behind_base=N` so the caller rebases deliberately. It still
  refuses the base branch as a target and a branch it would have to re-cut.
- **`… gains `rebase`**: fetch, and rebase the branch's commits onto the fetched tip. Up to date →
  no-op; behind and clean → rebased; **conflict → `rebase --abort`, every commit intact, exit 3**
  (distinct, so the caller pushes anyway and the PR's fix loop repairs the conflict, #475); dirty
  tree → refused; the base itself or a detached HEAD → refused.
- **`issue-bot.yml`'s commit step**: `make branch-adopt` before the commit, `make base-rebase` after
  it and before the push, treating exit 3 as "conflict, keep going". It no longer calls a
  base-asserting target after the work exists.
- **The patch artifact is uploaded on ANY rejected push** (`steps.push.outputs.pushed != 'true'`),
  not only on the workflow-scope rejection, so a finished implementation is never lost again.
- **Tests**: `adopt` from a behind HEAD (work kept, `behind_base=1`), attaching an existing branch,
  `rebase` up-to-date / behind / conflicting / dirty — all against REAL git repositories — plus the
  workflow guards, each proven RED against `origin/master`'s version of the step.

## Impact

`scripts/worktree_base.py`, `Makefile` (`branch-adopt`, `base-rebase`), `.github/workflows/issue-bot.yml`,
`tests/test_worktree_base.py`, `ARCHITECTURE.md` (§3 rows + the §10 inventory), `OPENSPEC.md`.

## Not covered

- **`AGENTS.md` §6n/§8 rows** for the commit-time pair — a protected file, refused in this
  environment; tracked on #494 with the wording (rule 3c).
- **A conflict-free guarantee.** A conflicted rebase still opens a PR that GitHub reports as
  conflicting; #475's repair loop fixes it. This change only guarantees the work survives.
