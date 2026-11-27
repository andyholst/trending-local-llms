# Proposal: goal-judge-served-pin-1798

Issue: #1798
PR: #1799

## Why

Hermes pauses a goal after five judge transport failures when `auxiliary.goal_judge` is pinned to a
Strata id the local server no longer serves. An explicit auxiliary provider does not walk the
profile's top-level `fallback_providers`, so a dead local judge route has nowhere to fall through.
The host files were corrected by hand on 2026-11-27, but re-rendering or re-provisioning from the
tracked configs cannot reproduce that correction because the renderer owns no `auxiliary:` block.

## What Changes

- `agents/model_chain.json` gains an optional `auxiliary.goal_judge` declaration that names a CHAIN
  ALIAS (never a duplicated model id) for the served local tier and the aliases forming its
  Nous fallback chain.
- `scripts/agent_model_chain.py` renders an `auxiliary.goal_judge` block into every generated lane
  config and refuses a chain whose judge alias is not its own `role=local_fallback` entry, whose
  fallback names the primary, or whose fallback is not a Nous step.
- `auxiliary` becomes an owned block in both `agent_model_chain.py` and `agent_profile_provision.py`,
  so a declared append may not redeclare it and a non-lane merge replaces it with the rendered one.
- The eight generated `agents/tll-*/config.yaml` files are regenerated from the chain.
- `tests/test_agent_model_chain.py` and `tests/test_agent_profile_provision.py` are extended.

## Impact

- Generated lane configs gain a deterministic `auxiliary.goal_judge` block; no hand-edit is needed.
- `make agent-model-chain-check` now refuses a judge pinned to any id other than the chain's own
  served local model.
- No credential value is introduced: every Nous step stays `provider: nous` with no `base_url`/`key_env`.
- Named quant aliases and the catalog mapping key are untouched (issue #1798 How §4).

## Not covered

- No host `~/.hermes/**` file is edited by this change (rule 3b backup/provision flows own that).
- No AGENTS.md rulebook section changes, so no rule-3c sign-off is owed.
- The chat-probe timeout recorded in `model_chain.json` is not re-investigated here.
