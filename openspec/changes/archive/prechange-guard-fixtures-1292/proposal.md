# Proposal: prechange-guard-fixtures-1292

Issue: #1292
PR: #1298

## Why

Two rule-6c regression guards (`tests/test_engagement_rollup_1182.py`,
`tests/test_stale_last_seen_gap.py`) proved "the old code is red" with
`git show origin/master:scripts/...`. In CI's shallow checkout that ref does not
exist, so `git show` returns empty and the negative assertions pass vacuously —
locking nothing. On a full clone that has fetched master, the modules now
contain the features, so the same assertions fail and red a correct tree. The
same guard is therefore false-green in CI and false-red on a full clone, for
reasons unrelated to the code it claims to protect.

## What Changes

- Pin the genuine pre-change blobs as in-memory fixtures in each test file,
  recovered verbatim from their adding commits' parents (`e2bad5f6^` for
  `recompute_7d_engagement`, `1a4c1e4e^` for the pre-`#1183` gaps block).
- Replace each `git show origin/master:...` probe with its fixture and add a
  loud authenticity guard that refuses an empty or garbled blob, so the test
  can never pass on empty output.
- Add the two authenticity tests to each suite's `main()` and update the
  module docstrings to name the fixture contract.

## Impact

Tests only. No data, contract, Makefile, workflow, image or production module
changes. The negative assertions keep the same semantics (pre-change code has
no post-counter rollup, no `stale_last_seen` signal); only their evidence
source becomes deterministic.

## Not covered

- No CI dispatch, no merge, no master push, no collaborator grant.
- No change to the features the guards protect (#1182, #1183).
