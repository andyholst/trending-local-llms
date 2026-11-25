# Proposal: free-model-refresh-fixture-drift

Issue: #1744
PR: pending

## Why

The weekly free-tier refresh is a live truth: `agents/model_chain.json` changed on 2026-11-25 from
five free ids to three (two retirements, one context drift). Three open keeper PRs (#1722/#1728/
#1738, plus #1746) went red at `validate` with identical failures in three unrelated test modules:
`tests/test_agent_model_chain.py` pinned `default: meituan/longcat-2.5:free`,
`tests/test_agent_profile_provision.py` pinned the same primary as a drift fixture, and
`tests/test_free_model_refresh.py` pinned `SHIPPED_FREE`, one retirement alias and one context-drift
id. A healthy refresh therefore reds the deterministic suite, and the keeper PRs can never merge.
Deleting the guards is not a fix: they prove rule 2 (no invented values), byte-identical no-ops,
retirement recording and local/paid tier preservation.

## What Changes

- Derive every free fixture — ids, context windows, primary, retirement alias — from the ONE
  source `agents/model_chain.json` at test time in the three test modules.
- Add `test_the_fixtures_follow_the_live_chain_not_a_snapshot`: a guard that fails when any
  currently-shipped free id is spelled out as a literal in those modules. It is catalogue-agnostic,
  so it stays green for any future live set while refusing a snapshot regression.
- Keep every behavioural assertion: byte-identical no-op, retirement announced AND recorded,
  added ids appended with their live context, local tier and paid pin untouched.
- No production script, Makefile, workflow or data-shape change. AGENTS.md §8's guard row is
  declared owed to the attended owner (rule 3c) in `findings/1744.md`.

## Impact

- Capability: `fleet-model-chain` (the test fixtures follow the live chain instead of a snapshot).
- Additive and non-breaking: production behaviour is byte-identical; only fixture derivation and
  one new guard change.
- The three open keeper PRs become mergeable once this fix lands on master and their heads are
  rebased onto it; this change does not force-push any other branch.
