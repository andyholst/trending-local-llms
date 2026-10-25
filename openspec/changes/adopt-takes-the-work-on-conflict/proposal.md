# A conflicted adopt keeps the run's work, never a conflict marker

**Issue:** [#583](https://github.com/andyholst/trending-local-llms/issues/583)
**Capability:** `worktree-base`

## Why

`#581` made `branch-adopt` carry a dirty tree onto an existing branch by stashing and popping.
A conflicted pop left `<<<<<<<` markers in the tree — and the next step is `git add -A` +
commit, so the markers were committed.

Measured on run **40202490846**: the markers landed in the **Makefile**, the commit succeeded,
and the very next target — `make base-rebase` — died with `Makefile:588: *** missing
separator` before anything was pushed. A marker inside a parsed file does not just look wrong;
it disables the build the fix loop needs to repair anything.

## What Changes

- **`scripts/worktree_base.py::mode_adopt`** — on a conflicted re-apply, each conflicted path
  keeps THIS RUN's side (`git checkout --theirs`, then `git add`), because the work being
  carried was written against the base as it is NOW while the branch's copy is the older
  attempt. `merge_conflict=<path,…>` names what was resolved; a path that cannot be resolved
  keeps its work in `git stash list` and says so.
- **`tests/test_worktree_base.py`** — the #580 case now also asserts the resolved content is
  the run's, `git grep -l '^<<<<<<<'` is EMPTY, and the resolution is reported by name.
- **`AGENTS.md`** §8 — the row is owed where the protected-file gate refuses the write; the
  exact text is in `findings.md`.

## Impact

The conflicted-adopt path only. A clean re-apply is unchanged; a first run is unchanged.

## Not covered (out of scope)

- The commit step still trusts `git add -A`; a marker from ANY other source (a botched manual
  merge) would still be committed. A guard at the commit step is filed as a finding.
- The stash entry a conflicted pop leaves is never pruned (#580's finding, still open).
