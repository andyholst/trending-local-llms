# Proposal: goal-judge-served-id

Issue: #1798
PR: #1800

## Why

Hermes pauses a goal after five judge transport failures when `auxiliary.goal_judge` is pinned to a Strata model the local server is not serving. An explicit auxiliary provider does not walk top-level `fallback_providers`. The rendered fleet configs name the served local id on `local-strata`, and they do not declare `goal_judge`, so a provisioned lane has no judge pin that follows the chain.

## What Changes

- `scripts/agent_model_chain.py` renders `auxiliary.goal_judge` from the chain's `local_fallback` (provider, model, base_url) and a `fallback_chain` of every other chain step: every `:free` Nous model, including the free primary, then the paid last resort. The local tier is not repeated. A `nous` hop stays provider and model only.
- `make agent-profile-model-render` rewrites every `agents/tll-*/config.yaml` from that renderer. The files are not hand-edited.
- `tests/test_agent_model_chain.py` locks the pin, the hop list, and the untouched free primary.
- The §8 row for that module names the new refusal.

## Impact

`model.default` stays the Nous free primary. No workflow, image, or contract file changes. Credential fields stay names; the judge block carries no `key_env`.

## Not covered

- Live `~/.hermes` profiles. This change is the repository render only.
- llgenie `agents/hermes-base-config.yaml` (asimov-agent/llgenie issue #3089).
