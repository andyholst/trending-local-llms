# Proposal: fleet-local-fallback-tier

Issue: #1192
PR: #1197

## Why

The owner directive of 2026-11-21 fixes ONE model order for every Hermes home the
repo renders and provisions: the live Nous **free** tier first (including
`qwen/qwen4-max:free`), the owner's **local strata box** second, and the paid pin
`deepseek/deepseek-v4-flash-0731` LAST. The chain (`agents/model_chain.json`,
issue #1140) cannot express that order today: `local_fallback` appears nowhere in
`scripts/agent_model_chain.py`, `scripts/agent_profile_provision.py` or their
tests (measured 2026-11-21, `grep -rn local_fallback scripts/ tests/` → 0 hits).
Meanwhile all 30 host homes (default + 29 profiles) sit `provider: strata` first
with a stale local id (`qwen3.8-flash-next-q2_0` in every config vs the live
server's `qwen3.8-flash-next-iq3_xxs`, measured `GET http://127.0.0.1:8080/v1/models`
2026-11-21) — the #1142 drift signature, plus a model id the server no longer serves.

## What Changes

- `agents/model_chain.json` gains ONE credential-less `role: "local_fallback"`
  entry between the free fallbacks and the paid `last_resort`: its own
  `provider: strata`, `base_url: http://127.0.0.1:8080/v1`, the live-probed bare
  model id and context window, NO `key_env` (rule 3e: a credential is a NAME
  only, and the local box needs none).
- `scripts/agent_model_chain.py` learns the tier: validation (position, count,
  shape), rendering (alias block + `fallback_providers` order), `--check` and
  `--report`. Every existing refusal is KEPT; the new tier adds its own.
- `tests/test_agent_model_chain.py` (+ `tests/test_agent_profile_provision.py`
  where its fixtures partition by role) updated in the same change (rules 6b/6c);
  each new refusal proved RED on the pre-change seam.
- The rendered lane configs are regenerated (`make agent-profile-model-render`);
  host provisioning is the explicit attended act that follows the merge
  (`make agent-profile-provision ALL=1` + non-lane homes + default).
- AGENTS.md §8 row for `tests/test_agent_model_chain.py` names the local tier
  (rule 3c: attended owner sign-off — the owner directed this change in session).

## Impact

- Capability: `fleet-model-chain` (the chain contract, its gate and its renderer).
- Additive only (rule 3b): no existing chain entry, alias, refusal or rendered
  key is removed or shrunk; the free steps and the paid pin stay byte-identical.
- No new make target, pipeline job or image: the tier rides the existing
  `agent-model-chain-check` (bundled in `make lint`) and `agent-profile-provision`
  seams, so rule 6d wiring is unchanged. `ARCHITECTURE.md` §6 rows stay true;
  the generated §10 block is refreshed in the same commit if any script
  docstring moves (rule 6h).

## Not covered

- The weekly free-model-refresh pipeline the owner asked for alongside this
  change is filed as its OWN issue (one issue per change, rule 6g/serial work);
  this change does not add a pipeline.
- Host provisioning itself is an attended act after the merge, not a repo edit;
  this change ships the chain + seams that make it one command.
- The free set is NOT re-listed from memory: the five free entries keep their
  recorded 2026-11-19 live read (`measured` block); a fresh live re-read rides
  the weekly-refresh issue. No id is invented (rule 2).
