## ADDED Requirements

### Requirement: The second batch of planner/implementer host-ahead notes is landed in the repo mirrors

The `tll-planner` and `tll-implementer` lane skill mirrors SHALL carry the four further host-ahead
pitfall rules merged additively into their own `## Pitfalls` lists: for planner, rule-3c protected
instruction files are owed to the owner and an auto-close can hide an undone half (verify the merged
PR's DIFF); for implementer, a rebase `--continue` can drop `--amend` edits and the merge-tree index
race is PER-MASTER-MOVE (`not mergeable` after green validate+live-smoke). Every rule SHALL keep its
reference and be byte-identical to the host text. No rule SHALL appear under a
`## Host notes ahead of master` header, and no host timestamp header, timestamp or machine-specific
name SHALL remain in the landed text. No `config.yaml` or `SOUL.md` is part of this change.

#### Scenario: Both mirrors carry the second batch with their references and no host stamps

- **Given** the `agents/tll-planner/skills/tll-planner/SKILL.md` and
  `agents/tll-implementer/skills/tll-implementer/SKILL.md` mirrors
- **When** the guard reads the skill texts
- **Then** each of the four new rules appears in the right lane's Pitfalls with its reference, and
  the host timestamp header, the host timestamp and the machine name appear nowhere
- **Test:** tests/test_fleet_lifecycle.py::test_lane_skill_mirrors_carry_landed_host_ahead_notes
