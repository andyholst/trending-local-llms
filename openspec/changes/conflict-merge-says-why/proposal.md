# A failed base merge names its paths, or names git's reason — never `<unreadable>`

**Issue:** [#563](https://github.com/andyholst/trending-local-llms/issues/563)
**Capability:** `bot-conflict-repair`

## Why

`scripts/fix_loop.sh::merge_base` merges the PR's base before the first LLM round (#475). On
failure it printed

```
[fix-loop] merging origin/master CONFLICTED in: <unreadable> — a Hermes round resolves it (issue #475)
```

Measured on run 40177729642 (fix-bot on PR #557): `git merge` failed and
`git diff --name-only --diff-filter=U` listed nothing, so the placeholder was printed, a
conflict report was written with empty paths, and every round was told to resolve a conflict
that did not exist — all three rounds then detached (`Input required; detached without
cancelling`) and the PR was left for manual review with no diagnosis.

A merge can legitimately fail WITHOUT an unmerged path: an untracked file the base would
overwrite, a dirty index, a git that refuses outright. Those are not conflict repairs, and
a round cannot act on them.

## What Changes

- **`scripts/fix_loop.sh`** — `merge_base` captures `git merge`'s own output and branches on
  whether there IS an unmerged path:
  - unmerged paths → unchanged behaviour (the report, the round, `--abort` at the end);
  - none → `REFUSED: … failed with NO unmerged path … git said: <git's first line>`, the
    working tree untouched, `BASE_CONFLICT_PENDING=0`, and the checks still run so the real
    failure is reported instead of being masked by a phantom repair.
  - The placeholder strings `<unreadable>` and `<git could not list them>` are gone: the loop
    either knows the paths or quotes git.
- **`tests/test_fix_loop.py`** — a real repository whose base adds a file the branch has
  untracked, asserting: no placeholder, the refusal names the reason git gave, no conflict
  report is handed to the round, the round still runs, and nothing is staged or half-merged.
- **`AGENTS.md`** §8 — the guard row (review-required, rule 3c).

## Impact

The fix loop's base-merge path only. A real conflict behaves exactly as before (its test is
unchanged and still green). No data, README or ranking change.

## Not covered (out of scope)

- The loop does not RETRY a base merge that failed for a non-conflict reason (an untracked
  file could be moved aside). It reports and continues, which is the safe half; filed as a
  finding.
- `scripts/fix_loop.sh` is still not reachable from a `make` target, so its merge path is
  exercised only by the fix-bot workflow and this suite (issue #482 tracks the inventory
  half).
