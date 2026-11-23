# Proposal: land-planner-implementer-skill-notes-1440

Issue: #1440
PR: #1441

## Why

`make fleet-host-sync-check BASE=origin/master` reds on two lane skills after #1418 landed and the
host re-synced: `tll-planner/skills/tll-planner/SKILL.md` and
`tll-implementer/skills/tll-implementer/SKILL.md` diverge because the host copies carry legitimate
notes AHEAD of master. Wiping them to force the gate green would destroy real experience and repeat
the false-alarm the gate exists to prevent; they must be landed through a reviewed change and then
re-synced. The third divergence (`tll-reviewer`) is tracked separately as #1432 / PR #1434.

## What Changes

- `agents/tll-planner/skills/tll-planner/SKILL.md`: add the additive host-ahead pitfall notes —
  verify a landed change against `origin/master` (throwaway detached worktree at the fetched sha),
  lanes change locally and PUSH while CI verifies (owner directive #1423), and separate WALL-CLOCK
  from CPU counting containers before calling a lane slow. Master's existing concurrency bullet and
  its `Repo guard: issue #1416` reference are kept verbatim.
- `agents/tll-implementer/skills/tll-implementer/SKILL.md`: add the additive host-ahead notes —
  the OpenSpec LIFECYCLE gate (`make openspec-archive-check PR=<n>`, remedy
  `make openspec-record-pr`, #866/#1434) and the local `test_engine_registry.py` / `GH_TOKEN`
  environment artifact (#972).
- Extend `tests/test_fleet_lifecycle.py::test_lane_skill_mirrors_carry_landed_host_ahead_notes`
  (already wired into `main()`) with the five new phrase/reference pairs so both mirrors are pinned.
- No `config.yaml`, `SOUL.md`, target, stage, workflow, contract or data change.

## Impact

Mirror/docs only. The gate is unchanged; after this merges the host re-syncs and
`make fleet-host-sync-check BASE=origin/master` reports 0 divergences on those two lanes.

## Not covered

- Re-syncing the host profile home — the owner/planner runs it after this merges.
- The `tll-reviewer` skill notes — #1432 / PR #1434 covers that lane.
