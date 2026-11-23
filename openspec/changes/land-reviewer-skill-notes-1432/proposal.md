# Proposal: land-reviewer-skill-notes-1432

Issue: #1432

## Why

`make fleet-host-sync-check BASE=origin/master` still reds on one lane skill after #1418 landed and
the host re-synced: `tll-reviewer/skills/tll-reviewer/SKILL.md` diverges because the host copy carries
two legitimate pitfall notes AHEAD of master. Wiping them to force the gate green would destroy real
experience and repeat the false-alarm the gate exists to prevent; they must be landed through a
reviewed change and then re-synced.

## What Changes

- `agents/tll-reviewer/skills/tll-reviewer/SKILL.md`: merge the OpenSpec-lifecycle note (`8b`) into
  the skill's existing numbered review list, keeping its #866 reference and its offline reproduction
  command (`python3 scripts/openspec_archive_check.py --pr <n>`).
- Same file: extend the existing hand-rolled-test-hygiene pitfall with the OTHER direction — a
  `test_*` listed twice in `main()` inflates the printed count — keeping the `test_workflows.py`
  reference.
- `tests/test_fleet_lifecycle.py::test_reviewer_skill_carries_landed_host_ahead_notes` pins both phrases and references inside the reviewer skill (the OpenSpec-lifecycle note is a numbered review step, so the check is whole-file), with no host timestamp header, timestamp or machine name.
- No `config.yaml`, `SOUL.md`, target, stage, workflow, contract or data change.

## Impact

Mirror/docs only. The gate is unchanged; after this merges the host re-syncs and
`make fleet-host-sync-check BASE=origin/master` reports 0 divergences.

## Not covered

- Re-syncing the host profile home — the owner/planner runs it after this merges.
- Any other lane's skill notes — #1418 covered planner/implementer.
