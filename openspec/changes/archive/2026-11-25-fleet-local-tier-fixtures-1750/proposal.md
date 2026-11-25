# Proposal: fleet-local-tier-fixtures-1750

Issue: #1750
PR: #1753

## Why

PR #1749 (issue #1744, merged as `620fa718`) added `tests/fleet_chain_fixtures.py` and removed the frozen *free* catalogue, but the credential-less local tier is a separate data surface that was left frozen. `tests/test_agent_model_chain.py:219-230` pins `qwen3.8-flash-next-iq3_xxs`, `local-strata`, `provider: strata`, `base_url: http://127.0.0.1:8080/v1` and the `nous-deepseek` boundary as literals, and `tests/test_agent_profile_provision.py:145-146` pins the same local model id. A future legitimate refresh that swaps the local model, its alias, its provider or its endpoint will turn these guards red while the seam under test stays correct — the exact fixture defect rule 6c forbids, one refresh later. This is the sibling finding recorded in `findings/1744.md`, filed as its own work item (rule 6g).

## What Changes

- Extend `tests/fleet_chain_fixtures.py` with ONE derivation of the local-tier needles — bare server model id, alias, provider, endpoint and the paid `last_resort` alias — read from the chain dict it is given (rule 6d, no second implementation).
- Refactor `tests/test_agent_model_chain.py` so the rendered-config fallback/local-alias guard derives every local-tier needle from the shipped chain through that seam; no frozen local literal remains in that guard.
- Refactor `tests/test_agent_profile_provision.py` so the "local tier survives only as a credential-less step" guard derives its model needle from the shipped chain.
- Add a synthetic-local-tier guard that is RED on the frozen shape and GREEN on the fix: a synthetic chain whose local model/alias/provider/endpoint appear in no old literal drives every new fixture, and the shipped needles are proved present in the rendered config.
- Keep every real guarantee: the local tier stays credential-less, keeps its own provider/endpoint, stays between the free fallbacks and the paid pin; hand-edit drift and chain-shape violations stay refused.

## Impact

Tests and one test-only helper module. No change to the chain, a lane config, the render/provision seams, a data contract, a workflow, a make target, `AGENTS.md` or a stored value. The two existing §8 rows already name both guard modules, so this adds no protected-rulebook row. A future local-tier refresh no longer reddens deterministic CI for a correct seam.

## Not covered

- No merge, no master push, no CI dispatch, no collaborator grant.
- No change to `AGENTS.md` (protected rulebook); no new rulebook row is owed.
- No change to the free-tier fixtures, the weekly free refresh, or the four keeper PRs it already serves.
- The `qwen3.8-flash-next-q2_0` literal in the provision tests stays frozen on purpose: it is the historical *stale home* fixture issue #1142 measured, not a shipped-chain value.
