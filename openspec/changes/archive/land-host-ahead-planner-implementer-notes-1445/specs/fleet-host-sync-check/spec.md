## ADDED Requirements

### Requirement: The tll-planner and tll-implementer host-ahead notes are landed, reconciled, in the repo mirrors

The `tll-planner` and `tll-implementer` lane skill mirrors SHALL carry the host-ahead pitfall rules
merged into their own `## Pitfalls` lists, additive to master's existing text: for planner, the
mechanical `make dispatch-check ISSUE=<n>` concurrency guard (#1416), the protected-instruction-file
rule (`agents/*/SOUL.md` and `AGENTS.md` §7b/§8; rule-3c) and the auto-close hidden-half check; for
implementer, the rebase `--amend`-message check (#1427) and the per-master-move merge-tree index race
(#1432). Every landed rule SHALL keep its issue reference (#1239, #712, #1416, #1423 in planner;
#866, #1434, #972, #1427, #1432 in implementer). Neither rule SHALL appear under a
`## Host notes ahead of master` header, and no host timestamp header, timestamp or machine-specific
name SHALL remain in the landed text. No `config.yaml` or `SOUL.md` is part of this change.

#### Scenario: Both mirrors carry the reconciled notes with their references

- **Given** the `agents/tll-planner/skills/tll-planner/SKILL.md` and
  `agents/tll-implementer/skills/tll-implementer/SKILL.md` mirrors
- **When** the guard reads the skill texts
- **Then** every landed rule appears with its reference and the host timestamp header, the host
  timestamp and the machine name appear nowhere
- **Test:** tests/test_fleet_lifecycle.py::test_lane_skill_mirrors_carry_landed_host_ahead_notes

#### Scenario: A home synced from the reconciled mirrors passes the real seam

- **Given** a scratch profile home copied from this tree's lane mirrors
- **When** the real `scripts/fleet_host_sync_check.py` seam runs against that tree
- **Then** it exits 0 — the landed mirrors are the bytes a re-synced host carries
- **Test:** tests/test_fleet_lifecycle.py::test_real_seam_accepts_a_synced_home
