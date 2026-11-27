# Proposal: planner-mirror-four-behaviors-1835

Issue: #1835
PR: #1855

## Why

Owner directive 2026-11-27 added four standing behaviors to the fleet: four instances of each
delegable lane with the planner single, autonomous pick-up from the issue comments, a weekly
lane-maintenance pass that is a cadence rather than a timer, and a per-host sync check. The
owner-mandated rule says a profile's `SOUL.md` and skill are updated first and the in-tree
`agents/` mirrors are refreshed afterwards so every host inherits them. The canonical docs on
master (`docs/fleet-collaboration.md` §3/§5/§6 and `docs/weekly-lane-maintenance.md`) already
carry the behavior; the two in-tree planner mirrors did not.

## What Changes

- Add `## Fleet scale, autonomous pick-up, weekly lane maintenance` to
  `agents/tll-planner/SOUL.md`, carrying the four-instances/single-planner roster, the
  self-claim-from-issue-comments rule with the claim-twice race guard and lease-checked push,
  and the weekly cadence-not-timer pass with its `docs/weekly-lane-maintenance.md` checklist.
- Add the `- **Per-host sync check runs from every LLM host.**` bullet to the `## Fleet` section
  of the same SOUL: fetch, re-read host and in-tree contracts, run
  `make fleet-host-sync-check BASE=origin/master` from that host, file drift, and never wipe
  runtime stamps or byte-copy a host-ahead note to force green.
- Add `## Fleet scale + autonomous pick-up` and `## Per-host sync check` guidance blocks to
  `agents/tll-planner/skills/tll-planner/SKILL.md`, matching the SOUL clauses.
- Add `findings/1835.md` and this OpenSpec change, and regenerate `OPENSPEC.md`.

## Impact

Prose only: +28 lines in the planner SOUL and +19 lines in the planner skill, with zero
deletions. No `AGENTS.md`, cron, GitHub Actions `schedule:`, stamped config file, `agents/README.md`,
`data/`, README, schema or workflow change. No guard is edited. The planner's `fleet-host-sync-check`
byte-compare may still report host-side drift — the planner ruling on #1835 records that host
drift as a separate known issue (#1745/#1576/#1579/#1580), explicitly not a blocker on this PR.

## Not covered

- No host profile file is edited; the host copies are a separate lane's responsibility.
- No merge, no master push, no manual CI dispatch, no new label, and no second issue is closed.
