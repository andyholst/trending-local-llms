# Adopting an existing branch carries the run's uncommitted work

**Issue:** [#580](https://github.com/andyholst/trending-local-llms/issues/580)
**Capability:** `worktree-base`

## Why

`make branch-adopt` attaches the implementer's branch at COMMIT time (issue #500). When the
branch already exists on `origin` — the RE-RUN shape, an issue that already has an open PR —
it ran `git checkout -B <branch> refs/remotes/origin/<branch>`, which git refuses while the
working tree is dirty:

```
REFUSED: `git checkout -B ci/data-gap-362-… refs/remotes/origin/ci/data-gap-362-…` failed (1):
error: Your local changes to the following files would be overwritten by checkout
```

Measured on run **40199055887** (owner dispatch, 2026-10-25): the agent had implemented for
~20 minutes, `branch-adopt` refused, and the run ended with no commit, no push, no PR, and
no patch artifact — the whole sweep lost. The tree is dirty BY DESIGN there: it holds the
implementation being adopted.

`pick` succeeded in the same run (#577), so this was the last structural stop between a
working pick and a green sweep.

## What Changes

- **`scripts/worktree_base.py::mode_adopt`** — when the tree is dirty AND the branch already
  exists (local or remote), the work is STASHED first, the branch is attached, and the stash
  is re-applied. The work is never dropped:
  - a clean re-apply restores the tree exactly (`how=existing-remote-reapplied`);
  - a conflicting re-apply keeps the stash entry AND leaves the markers in the tree, and
    prints `merge_conflict=true` — the same contract the fix loop already resolves;
  - the `cut-from-head` path (no existing branch) is untouched: `git checkout -b` at HEAD
    already carries the tree.
- **`tests/test_worktree_base.py`** — a real repository with a remote branch that changed
  `f.txt`, a dirty `f.txt`, a new file and an untracked file: the adopt succeeds, the earlier
  commit is intact, the work is kept (restored or conflicted), and nothing is silently lost.
- **`AGENTS.md`** §8 — the row is owed where the protected-file gate refuses the write; the
  exact text is in `findings.md`.

## Impact

The adopt path on a re-run only. A first run (no branch) behaves exactly as before, and its
test is unchanged and still green.

## Not covered (out of scope)

- A dirty tree whose change conflicts with the branch is left CONFLICTED for the fix loop
  rather than auto-resolved: resolving a conflict is a judgement, and the loop exists for it.
- `git stash pop` on a conflict leaves the stash entry; nothing prunes it, so a run that ends
  conflicted leaves a stash behind (filed as a finding).
