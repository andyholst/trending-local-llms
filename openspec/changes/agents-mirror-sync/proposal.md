# In-tree fleet mirror resync from current host profiles, + the two new lanes

**Issue:** [#696](https://github.com/andyholst/trending-local-llms/issues/696)
(**#703** references the SOUL uplift this keeps the repo aligned with)
**Capability:** `agents-mirror-sync`

## Why

Each lane's `agents/<profile>/SOUL.md` and `agents/<profile>/skills/<profile>/SKILL.md`
are the in-tree records of the host Hermes profiles for https://github.com/andyholst/
trending-local-llms. The committed copies were stale: they predated the #690 delivery
rules and the #703 "Standing rules / CLAIM-READ-REPORT" behavior lift, and they did not
include the two lanes the fleet gained (`tll-tester`, `tll-pr-rebase`). The README fleet
table likewise lacked those two rows.

This change re-copies EVERY current host SOUL + skill (all seven lanes) into the in-tree
mirror so the repo matches what the host actually runs, and adds the two missing fleet
rows to the README. Docs-only: no code, schema, data, workflow, cron, or GitHub Actions
schedule change.

## Delivery

- `agents/tll-planner/`, `agents/tll-architect/`, `agents/tll-tester/`,
  `agents/tll-reviewer/`, `agents/tll-security/`, `agents/tll-implementer/`,
  `agents/tll-pr-rebase/` — each `SOUL.md` + `skills/<profile>/SKILL.md` re-copied
  byte-faithful from that lane's CURRENT host profile; the `tll-tester` and
  `tll-pr-rebase` directories are new to the tree.
- `agents/README.md` — fleet table gains the `tll-tester` and `tll-pr-rebase` rows.
- `openspec/changes/agents-mirror-sync/` — this change dir.
