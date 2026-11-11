# `git_out` strips its output, so a record parser needs `git_raw`

**Issue:** [#504](https://github.com/andyholst/trending-local-llms/issues/504)
**Capability:** `worktree-base`

## Why

`git_out` returns `proc.stdout.strip()`. That is right for a VALUE (`rev-parse HEAD`) and wrong for
a RECORD: `git status --porcelain` writes `XY<space>PATH`, so stripping a line drops the leading
status space and shifts the path. The first `refresh_base._dirty_paths` parsed porcelain through it
and reported `EADME.md` for a modified `README.md`.

The trap is silent — the caller gets a well-formed string that is wrong — and nothing documented
the stripping, so the next caller can repeat it.

## What Changes

- **`scripts/worktree_base.py`** — `git_out`'s docstring now states that it strips and that a
  porcelain/`-z` parser must use **`git_raw`**, a new sibling that returns stdout exactly as git
  wrote it (same `git` call, same failure reporting, so the only difference is the stripping).
- **`tests/test_worktree_base.py`** — `test_git_out_strips_and_git_raw_does_not` drives both reads
  in a real repository and proves the difference end to end: `git_raw` keeps the leading status
  byte and `-z` NUL separators; a naïve porcelain parser reads the whole path through `git_raw`;
  the same parser mangles the first path through `git_out` — the measured defect, pinned.

## Impact

Callers can now choose deliberately, and the choice is documented where the helper lives.

## Not covered (out of scope)

- Existing callers are left as they are: each is a value read or already raw (`refresh_base` reads
  `git()` directly and splits on NUL). Auditing them one by one is filed as a finding.
