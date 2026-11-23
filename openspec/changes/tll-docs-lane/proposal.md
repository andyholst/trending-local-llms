# Proposal: tll-docs-lane

Issue: #1396

## Why

`tll-planner`'s skill already names a `tll-docs` lane and issue #691 decomposed it into three slices, but the lane itself does not exist: no `agents/tll-docs/`, no profile, no row in the fleet table. Slices A (#1394) and B (#1395) land the guard and the page; nothing owns the lane that keeps them true afterwards, so the next contract or store change again leaves the prose behind. The lane set is DERIVED (`agent_model_chain.fleet_lanes` reads `agents/tll-*/SOUL.md`), so standing the lane up is a mirror-and-list change, not a code change.

## What Changes

- Add `agents/tll-docs/{SOUL.md,skills/tll-docs/SKILL.md,config.yaml}`: the docs capability owner (schema⇄contract sync, the store architecture page, doc gaps left by delivered PRs). `config.yaml` is rendered by `make agent-profile-model-render` from the ONE chain, byte-identical to every other lane.
- Add the `agents/README.md` row and correct the fleet count in `AGENTS.md` §7b from seven to eight, with the `tll-docs` remit named.
- Add `tll-docs` to the four hand-kept lane lists: `scripts/fleet_host_sync_check.py`'s `LANES`, `tests/test_fleet_lifecycle.py`, `tests/test_fleet_handover_protocol.py`, `tests/test_host_fleet_souls.py`.
- Add `tests/test_fleet_lifecycle.py::test_the_lane_set_is_derived_and_the_new_lane_is_wired`: the guard's `LANES`, the seam's `LANES` and the guard lists must equal `agent_model_chain.fleet_lanes(ROOT)` — a lane added to the tree but missing from any list is a lane the host-sync gate never compares.
- Mark `tll-planner`'s skill line that names `tll-docs` as proposed, so the planner reads it as stood up.

## Impact

No data format, contract, workflow, image, target or schedule change. The lane is inert until the owner provisions its profile on a host (as #696 ruled for a new profile) — this change lands the tracked files only. Every existing lane's remit is unchanged; the only rulebook edit is the §7b count and the remit sentence.

## Not covered

- No profile provisioning on any host (owner act), no `hermes` session, no cron.
- No `AGENTS.md` §6b pipeline-list change: no workflow is added.
- No change to the README renderer, `data/`, a contract JSON or an image.

## Rule 3c

This change edits protected `AGENTS.md` §7b (the fleet count and the `tll-docs` remit). A headless leg may not write the rulebook: the box is recorded `- [~] … blocked: rule 3c human sign-off` and the owed row is filed for an attended run.
