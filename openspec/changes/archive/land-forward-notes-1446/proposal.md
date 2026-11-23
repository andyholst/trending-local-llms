# Proposal: land-forward-notes-1446

Issue: #1446
PR: #1448

## Why

`make fleet-host-sync-check BASE=origin/master` still reds on `tll-planner/SKILL.md` and
`tll-implementer/SKILL.md`: their host copies carry four further legitimate notes added AFTER PR
#1441/#1434 landed their first batches. Wiping the host files to force the gate green would destroy
real experience, so the notes must be landed through a reviewed change and the host re-synced.

## What Changes

- `agents/tll-planner/skills/tll-planner/SKILL.md`: add two additive host-ahead pitfall notes —
  rule-3c protected instruction files are owed to the owner (never route around a timed-out approval),
  and an auto-close can hide an undone half (verify the merged PR's DIFF, not its `Closes #` line).
- `agents/tll-implementer/skills/tll-implementer/SKILL.md`: add two additive host-ahead pitfall
  notes — a rebase `--continue` can drop `--amend` edits (re-check the message before every push),
  and the merge-tree index race is PER-MASTER-MOVE (`not mergeable` after green validate+live-smoke).
- Extend `tests/test_fleet_lifecycle.py::test_lane_skill_mirrors_carry_landed_host_ahead_notes`
  (already wired into `main()`) with the four new phrase/reference pairs.
- No `config.yaml`, `SOUL.md`, target, stage, workflow, contract, rulebook or data change.

## Impact

Mirror/docs only. The gate is unchanged; after this merges the host re-syncs and those two lanes
report fewer divergences. The remaining host divergences are rewrites of existing notes that need a
precedence ruling and are explicitly out of scope here.

## Not covered

- Re-syncing the host profile home — the owner/planner runs it after this merges.
- The rewritten concurrency / `OPENSPEC.md` bullets in the host copies: those need a decision on
  which wording wins and belong in their own reviewed change.
