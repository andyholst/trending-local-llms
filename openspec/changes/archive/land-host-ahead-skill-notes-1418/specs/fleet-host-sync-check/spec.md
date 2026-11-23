## ADDED Requirements

### Requirement: The host-ahead lane skill notes are landed, reconciled, in the repo mirror

The `tll-planner` and `tll-implementer` lane skill mirrors SHALL carry the host-ahead pitfall rules
merged into each skill's own `## Pitfalls` list — never under a `## Host notes ahead of master`
header — and every landed rule SHALL keep its issue reference. No host timestamp header, host
timestamp or machine-specific name SHALL remain in the landed text. A lane `config.yaml` is NOT part
of this change.

#### Scenario: Both mirrors carry the reconciled notes with their issue references

- **Given** the `agents/tll-planner/skills/tll-planner/SKILL.md` and
  `agents/tll-implementer/skills/tll-implementer/SKILL.md` mirrors
- **When** the guard reads each skill's `## Pitfalls` section
- **Then** every landed rule appears there with its issue reference, and the host timestamp header,
  the host timestamp and the machine name appear nowhere in either file
- **Test:** tests/test_fleet_lifecycle.py::test_lane_skill_mirrors_carry_landed_host_ahead_notes

#### Scenario: A home synced from these mirrors passes the real seam

- **Given** a scratch profile home copied from this tree's lane mirrors
- **When** the real `scripts/fleet_host_sync_check.py` seam runs against that tree
- **Then** it exits 0 — the landed mirrors are the bytes a re-synced host carries
- **Test:** tests/test_fleet_lifecycle.py::test_real_seam_accepts_a_synced_home
