# Proposal: pre-change-guard-blob-pin

Issue: #1292
PR: #1299

## Why

Two regression guards prove themselves RED on the pre-change code by reading
`git show origin/master:<path>` (`tests/test_engagement_rollup_1182.py`,
`tests/test_stale_last_seen_gap.py`). That probe is broken in BOTH directions
(issue #1292, measured on a clean worktree at `46e6fa6d`):

- on a FULL clone `origin/master` now CONTAINS the feature, so the negative
  assertion is false and `make test` reds a correct tree (147 passed, 2 failed);
- in CI the checkout has no `origin/master` ref, so `git show` answers empty and
  the assertion is VACUOUSLY true — the guard locks nothing.

A guard that is green for the wrong reason is the false-green class rule 6c
exists to remove, and here it sits on `master` itself.

## What Changes

- `tests/test_engagement_rollup_1182.py`: pin the pre-change blob by the
  immutable SHA `30c8f5f43500577e2f00af3d749e96b872650cdf` (the parent of the
  #1182 rollup commit `d4ad144`), read it with `git show <sha>:…`, and FAIL
  loudly — never pass — when that blob cannot be resolved or no longer carries
  the probed function.
- `tests/test_stale_last_seen_gap.py`: the same pin for
  `71b158aa0d30d8ec650af6f444fdfa1cbbd0879e` (the parent of the #1183
  `stale_last_seen` commit `6e71b2c`).
- Both guards additionally assert the probe actually FOUND the seam, so an
  empty blob can never read as a pass again.

## Impact

Test-only. No data, contract, Makefile target, workflow, image or rulebook
change. `make test` goes green on a full clone and stays green in CI for the
same reason — the pinned blob resolves in both — instead of being green in one
and red in the other.

## Not covered

- `tests/test_auto_merge_rebase.py`'s conditional `origin/master` workflow probe
  (a third instance of the same class, reported as a finding — rule 6g).
- Any change to the guards' subject matter (the #1182 rollup, the #1183
  `stale_last_seen` signal).
