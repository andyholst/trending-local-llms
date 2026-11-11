# A conflicted rebase is success, not failure

**Issue:** [#586](https://github.com/andyholst/trending-local-llms/issues/586)
**Capability:** `worktree-base`

## Why

`scripts/worktree_base.py rebase` exits **3** when the rebase conflicts, because a conflicted
rebase KEEPS every commit and the push must still happen (#475/#500). The issue-bot commit step
compared `make`'s status to 3 — but **make returns 2 for ANY failing recipe** and prints the
child's code only inside its own message (`make: *** [Makefile:403: base-rebase] Error 3`).

So the exit-3 branch was dead code. Measured on run **40205472559**: the run implemented for ~20
minutes, committed (`6 files changed, 213 insertions(+)`), `base-rebase` reported
`rebase=conflict` / `conflicted=README.md`, and the step refused to push with
`rc=2 — refusing to push a tree whose base could not be established`.

## What Changes

- **`Makefile`** — the `base-rebase` target normalises the documented code: a conflicted rebase
  prints `base_rebase=conflict` and exits **0**; a genuine failure (no branch, unreachable base,
  broken tree) still exits non-zero. The recipe is written `rc=0; cmd || rc=$?` so it behaves
  the same under make's `sh -c` and under `bash -e`.
- **`.github/workflows/issue-bot.yml`** — the step calls `make base-rebase BRANCH="$BRANCH"` and
  no longer compares an exit code an intermediary rewrites.
- **`tests/test_base_rebase_exit_code.py`** (new) — runs the REAL recipe text out of the Makefile
  against a stub `scripts/worktree_base.py` exiting 3 / 1 / 2 / 4 / 0.

## Impact

Every bot run that commits onto a base that moved. A conflicted rebase now reaches the push, and
the PR carries the conflict for the fix loop (#475) exactly as the rule says.

## Not covered (out of scope)

- A branch hundreds of commits behind replays its whole ancient history through the rebase (the
  measured branch was `ahead_base=273`), so the conflict is near-certain. Branch hygiene for
  stale implementer branches is filed as a finding.
