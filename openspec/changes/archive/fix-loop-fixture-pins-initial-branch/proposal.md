# Fix-loop fixtures pin their scratch branch

**Issue:** #1090
PR: #1112
**Capability:** `test-fixture-determinism` (the scratch git fixtures in
`tests/` decide their branch names from the fixture, never from the host's
`init.defaultBranch`).

## Why

`tests/test_fix_loop.py`'s base-merge fixtures built their scratch repos with
bare `git init` / `git init -q --bare`. A bare origin's `HEAD` symbolic-ref is
created from the **host's** `init.defaultBranch`, so on a host whose default is
`main` (git ≥ 2.28 default; this host: git 2.54.0 Apple Git-157 with no `[init]`
section) the origin's `HEAD -> refs/heads/main` dangles — only `master` is ever
pushed — and `git clone` warns "remote HEAD refers to nonexistent ref, unable
to checkout" and lands an EMPTY working tree. The next `git commit -qam` then
fails "nothing added to commit but untracked files present", red-ing
`test_a_conflicting_base_merge_is_handed_to_a_round_and_aborted_if_hopeless`
locally while GitHub-hosted runners (default `master`) stayed green — a local
red that blocks the pre-push gates this repo depends on (measured at `bafeb8d`
and again on this host on 2026-11-17: 67 passed, 1 failed).

## What Changes

- `tests/test_fix_loop.py`: every scratch fixture that clones or pushes `master`
  now pins its initial branch — `git init -q --bare -b master` for the three
  bare origins and `git init -q -b master` for the three work repos (and the
  no-progress repo). The one fixture that deliberately exercises a `main`
  default keeps its explicit `-b main`.
- `tests/test_fix_loop.py` gains `test_the_scratch_fixtures_pin_their_initial_branch`:
  a mechanical guard that reads the module's own source and refuses any scratch
  `git init` call without an explicit `-b <branch>` — RED on the pre-fix file.

## Impact

- `tests/test_fix_loop.py` — six fixture calls pinned, one new guard test.
- No production code, no Makefile target, no workflow changes.

## Not covered

- Other test modules' scratch repos (none observed to clone across a dangling
  bare HEAD; the new guard is scoped to this module where the defect lived).
- The host's own `~/.gitconfig` (the fix makes the suite independent of it,
  which is the point).
