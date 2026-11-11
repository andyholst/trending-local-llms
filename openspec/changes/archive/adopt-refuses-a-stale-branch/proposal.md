# Adopt refuses a branch that is not this run's work

**Issue:** [#592](https://github.com/andyholst/trending-local-llms/issues/592)
**Capability:** `worktree-base`

## Why

`branch-adopt` resumes an existing branch by **switching the tree to it**. When the branch is far
ahead of the base — an abandoned attempt from another day rather than a re-run of the same issue —
the switch **removes every file the base has added since**, and the steps after it run `make`
against a tree older than the `Makefile` that invoked them.

Measured on run **40210081952**: `OK: adopted ci/data-gap-362-… on 96bf0c2e7a33
(existing-remote-reapplied)`, `behind_base=1`, and the branch `/ahead_base=273` — then
`python3: can't open file '.../scripts/check_conflict_markers.py': [Errno 2] No such file or
directory`, because the adopt had just deleted a file master merged 30 minutes earlier. The same
drift is why `base-rebase` replays ancient history and conflicts on `README.md` every time.

## What Changes

- **`scripts/worktree_base.py::mode_adopt`** — before touching the tree, compute how many commits
  the branch carries that the base does not have. Above `RESUME_MAX_AHEAD` (default **20**) it
  **refuses**: `REFUSED: <branch> carries N commit(s) the base does not have (M behind it) — that
  is not a re-run of THIS issue's work…`, naming the remedy (close the PR, delete the branch, or
  pass `--resume-stale`). The refusal happens **before** any stash or checkout, so the run's own
  work and HEAD are untouched.
- **`--resume-stale`** (or `RESUME_STALE=1`) is the explicit human override.
- **`tests/test_worktree_base.py`** — a real repository with a branch carrying 5 commits: the adopt
  refuses (exit 1), names the counts and the remedy, leaves the work and HEAD and the stash list
  untouched, and `--resume-stale` still adopts it. A second case proves a re-run's OWN one-commit
  branch is still adopted, so the refusal does not block what the seam exists for.

## Impact

Every resuming run. A stale branch now fails loudly **before** the tree is rewound, instead of
silently leaving the run to die on a missing file two steps later.

## Not covered (out of scope)

- The branch is still there after the refusal: deleting it stays the operator's decision (it may
  belong to an open PR a human is reading). The refusal names it so the fix is one command.
