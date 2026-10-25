# A conflict marker never reaches a commit

**Issue:** [#588](https://github.com/andyholst/trending-local-llms/issues/588)
**Capability:** `bot-commit-safety`

## Why

`#583` fixed the one PRODUCER of conflict markers it knew about: a conflicted `branch-adopt`
re-apply, which left `<<<<<<<` in the tree and let `git add -A` commit it. Measured on run
40202490846 the markers landed in the **Makefile**, the commit succeeded, and the next target
died with `Makefile:588: *** missing separator` — after which nothing in the run could be
repaired, because every `make` had to parse the broken file first.

That fix is producer-side. Nothing stops the next source: a botched manual merge, a salvaged
detached run, an operator's `git stash pop`, a future tool. Both bots still commit with `git add
-A` and no check at all.

## What Changes

- **`scripts/check_conflict_markers.py`** — reads `git ls-files` and fails, naming every path and
  line, when a tracked file carries a git conflict block (`<<<<<<<`, `=======`, `|||||||`,
  `>>>>>>>` at the start of a line). It skips binary files (a NUL byte in the first 8000), so a
  marker-shaped byte sequence inside an image is not a finding, and it never sees an ignored or
  untracked file.
- **`make check-conflict-markers`**, wired into `make lint` (a marker in the repository is never
  acceptable) and called by BOTH bot commit steps **immediately before `git add -A`**, so a
  marker stops the commit instead of reaching a PR.
- **`tests/test_conflict_marker_guard.py`** (new) — real git repositories: a committed marker
  block is refused and named; a clean tree passes; an ignored/untracked scratch file and a binary
  are not findings; all four marker shapes count; a 6-character markdown rule does not; and both
  workflows run the target before `git add -A`.

## Impact

Both bots, and `make lint` on every PR. The measured failure (a committed marker making every
`make` unusable) now stops at the commit step with the paths named.

## Not covered (out of scope)

- Markers still reach the working tree (the adopt now takes a side instead of leaving them, but a
  manual merge can); they are refused at the commit, not prevented. Preventing them is the
  producer's job, per producer.
