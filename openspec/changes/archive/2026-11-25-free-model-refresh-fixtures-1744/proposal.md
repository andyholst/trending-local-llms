# Proposal: free-model-refresh-fixtures-1744

Issue: #1744

## Why

Three weekly `ci/free-model-refresh-*` keeper PRs (#1722, #1728, #1738, then #1746) were all red at `validate` with the same guards. The 2026-11-25 live free-tier refresh legitimately retired `meituan/longcat-2.5:free` and `qwen/qwen4-max:free`, promoted `tencent/hy4-flash:free` to primary and changed a context length. The guards in `tests/test_free_model_refresh.py`, `tests/test_agent_model_chain.py` and `tests/test_agent_profile_provision.py` froze a snapshot of the 2026-11-21 catalogue as literals, so a correct refresh reddened the deterministic suite while the seam under test stayed correct. Rule 6c: this is a fixture defect, not a script regression.

## What Changes

- Add `tests/fleet_chain_fixtures.py`: ONE derivation of free steps, primary, alias order, fallback model order and the rendered `default:` needle from a chain dict read at test time (rule 6d — one implementation).
- Refactor the three guard modules to derive their fixtures from the shipped `agents/model_chain.json` through that seam: no frozen free ids, aliases or context values remain in them.
- Add one guard that fails on the frozen shape and passes on the fixed head: a synthetic chain whose ids/aliases appear in no old literal drives every fixture, plus the shipped fixture must equal the shipped chain's free steps.
- Keep every real guarantee: rule 2 no invented values, byte-identical no-op, retirement announced AND recorded, local tier and paid pin untouched, hand-edit drift refused.

## Impact

Tests and a test-only helper module. No change to the chain, the refresh seam, a data contract, a workflow, a make target or a stored value. The four already-open keeper PRs are left untouched; after this change lands their branches need a rebase onto the new base so their CI runs the fixed guards (recommendation to the planner, no force-push without a signed handover).

## Not covered

- No merge, no master push, no CI dispatch, no collaborator grant.
- No change to `AGENTS.md` (protected rulebook) and no new rulebook row.
- Rebasing or closing the four keeper PRs — reported to the planner, not performed here.
