# Proposal: land-host-ahead-planner-implementer-notes-1445

Issue: #1445
PR: #1449

## Why

`make fleet-host-sync-check BASE=origin/master` reds on two lane skills: the host copies of
`tll-planner/skills/tll-planner/SKILL.md` and `tll-implementer/skills/tll-implementer/SKILL.md`
are AHEAD of master with legitimate pitfall notes measured since #1441 landed. Overwriting the host
to force the gate green would destroy unpublished work, so the notes are landed through this reviewed
change (the #1440 pattern) and the host re-syncs from the merged tree afterwards.

## What Changes

- `agents/tll-planner/skills/tll-planner/SKILL.md`: adopt the host-ahead concurrency rewrite (the
  mechanical `make dispatch-check ISSUE=<n>` guard, #1416), add the protected-instruction-files rule
  (`agents/*/SOUL.md` and `AGENTS.md` §7b/§8 are rule-3c protected) and the auto-close hidden-half
  check, and restore the issue references the host copy dropped (#1239, #712, #1416, #1423). The
  verify-against-`origin/master` bullet moves beside the related owner-checkout rule, as on the host.
- `agents/tll-implementer/skills/tll-implementer/SKILL.md`: add the rebase `--amend`-message note
  (#1427) and the per-master-move merge-tree index race note (#1432), carry the lifecycle example,
  and restore the dropped references (#866, #1434, #972).
- Extend `tests/test_fleet_lifecycle.py::test_lane_skill_mirrors_carry_landed_host_ahead_notes` with
  the new phrase/reference pairs.
- No `config.yaml`, `SOUL.md`, target, stage, workflow, contract or data change.

## Impact

Mirror/docs only. The seam is unchanged; after this merges and the host re-syncs,
`make fleet-host-sync-check BASE=origin/master` reports 0 divergences on both lanes.

## Not covered

- Re-syncing the host profile home — the owner/planner runs it after this merges.
- PR #1424 (#1423) — a separate in-flight change to the same two files; this branch rebases onto it.
