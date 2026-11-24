## ADDED Requirements

### Requirement: The implementer mirror carries the rebase-conflict pitfall

The tll-implementer `SKILL.md` mirror SHALL carry the `OPENSPEC.md` rebase-conflict lesson
reconciled into its own Pitfalls list, exactly once, with no host timestamp header, machine
name or absolute path, and SHALL keep the `#1363`/`PR #1609` reference.

#### Scenario: The note is landed, reconciled and unstamped

- **Given** the mirrored `agents/tll-implementer/skills/tll-implementer/SKILL.md`
- **When** the lifecycle guard runs
- **Then** the note appears exactly once between the `## Pitfalls` heading and the
  `## Switch-over` section, keeps both issue references, and carries no host timestamp header,
  timestamp or machine name
- **Test:** tests/test_fleet_lifecycle.py::test_implementer_mirror_carries_the_rebase_conflict_note
