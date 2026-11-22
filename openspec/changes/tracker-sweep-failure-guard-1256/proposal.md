# Proposal: tracker-sweep-failure-guard-1256

Issue: #1256
PR: pending

## Why

The 04:27 tracker sweep closed #827/#828 as OBSOLETE on four later green
`issue-bot` runs. `make pipeline-failure-guard-check` reds a CLOSED diagnosed
row with no fix PR and no guard test on EVERY PR; 12 open PRs were affected
within the hour. Non-recurrence is an observation, not a landed fix.

## What Changes

- AGENTS.md §6b gains a bullet: a tracker sweep may close a
  `pipeline-run-failure` issue only when its ledger row names a merged fix PR
  and a collected guard test (or was attributed through
  `make pipeline-failure-attribute`). Later green runs alone leave it OPEN.
- AGENTS.md §8 gains one regression row.
- `tests/test_tracker_sweep_closure_guard.py` pins both needles and is RED on
  the base rulebook.

## Impact

- AGENTS.md §6b/§8 and one new test module; no workflow, make target, script,
  data format or CI dispatch change.
- Rule 3c review-required; declared on issue #1256 before implementation.

## Not covered

- No change to `pipeline_failure_guard_check.py` (the gate is correct).
- No reopening of any other issue by this change; #827/#828 were restored
  separately.
