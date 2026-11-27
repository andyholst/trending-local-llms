# Proposal: live-free-tier-verification-1226

Issue: #1226
PR: #1227

## Why

The chain's free tier is a live truth, but the refresh seam writes nothing when the live set
equals the chain's (`scripts/free_model_refresh.py`, no-op path). A verification therefore leaves
no trace: a freshly checked chain is indistinguishable from one nobody checked for months. The
live Nous read of 2026-11-21T20:14:30Z (415 models, exactly five `:free` ids, all matching the
shipped windows) and the byte-for-byte equality of all 30 host `config.yaml` files with the repo
chain are real measurements with no record in the tree (rule 2 — a measurement must trace to a
read).

## What Changes

- Add an additive `measured.verified` record to `agents/model_chain.json` naming the live read
  (UTC timestamp, endpoint, catalogue count, free count and the five free ids). No existing key,
  alias, model, window or value is removed or rewritten (rule 3b).
- Lock the record with a new behavioural assertion in `tests/test_agent_model_chain.py`: the
  recorded ids/count equal the chain's actual free steps, the endpoint matches the chain's
  `base_url`, and the record names no credential field.
- OpenSpec capability spec + this checklist. All 30 host homes already match the rendered chain;
  this change neither writes host files nor dispatches a pipeline.

## Impact

- Capability: `fleet-model-chain` (the chain's measurement provenance, not its ordering contract).
- No make target, pipeline job, script image or Makefile pin changes; rule 6d/6h wiring is unchanged.
- The free model set, local strata tier and paid `last_resort` stay byte-identical.

## Not covered

- Changing the free tier itself: the 20:14Z live read returned the same five ids and windows the
  chain already carries, so no model edit is owed.
- The host's durable credential name (#1196), the host provisioning seam (#1204/#1211) and the
  local box's chat-completion hang (#1194) are separate filed issues.
- No merge, CI dispatch or PR creation beyond this change's own PR.
