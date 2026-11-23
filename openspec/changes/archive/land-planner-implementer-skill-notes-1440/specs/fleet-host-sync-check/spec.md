## ADDED Requirements

### Requirement: The tll-planner and tll-implementer host-ahead notes are landed, reconciled, in the repo mirrors

The `tll-planner` and `tll-implementer` lane skill mirrors SHALL carry the host-ahead pitfall rules
merged additively into their own `## Pitfalls` lists: for planner, verify against `origin/master` in a
throwaway detached worktree, lanes change locally and PUSH for CI to verify (#1423), and separate
WALL-CLOCK from CPU counting containers; for implementer, the OpenSpec LIFECYCLE gate
(`make openspec-archive-check PR=<n>` / `make openspec-record-pr`, #866/#1434) and the local
`test_engine_registry.py` / `GH_TOKEN` environment artifact (#972). Every rule SHALL keep its issue
reference. Master's existing concurrency bullet and its `Repo guard: issue #1416` reference SHALL be
preserved verbatim (additive only, rule 3b). Neither rule SHALL appear under a
`## Host notes ahead of master` header, and no host timestamp header, timestamp or machine-specific
name SHALL remain in the landed text. No `config.yaml` or `SOUL.md` is part of this change.

#### Scenario: Both mirrors carry the reconciled notes with their references and master's existing text

- **Given** the `agents/tll-planner/skills/tll-planner/SKILL.md` and
  `agents/tll-implementer/skills/tll-implementer/SKILL.md` mirrors
- **When** the guard reads the skill texts
- **Then** every landed rule appears with its reference, the `Repo guard: issue #1416` line is still
  present, and the host timestamp header, the host timestamp and the machine name appear nowhere
- **Test:** tests/test_fleet_lifecycle.py::test_lane_skill_mirrors_carry_landed_host_ahead_notes

#### Scenario: A home synced from the reconciled mirrors passes the real seam

- **Given** a scratch profile home copied from this tree's lane mirrors
- **When** the real `scripts/fleet_host_sync_check.py` seam runs against that tree
- **Then** it exits 0 — the landed mirrors are the bytes a re-synced host carries
- **Test:** tests/test_fleet_lifecycle.py::test_real_seam_accepts_a_synced_home
