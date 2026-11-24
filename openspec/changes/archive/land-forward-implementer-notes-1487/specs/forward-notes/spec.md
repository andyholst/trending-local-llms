# Capability spec: forward host notes land additively

## ADDED Requirements

### Requirement: Curated implementer notes reach master exactly once

The implementer skill mirror SHALL carry each genuinely-new forward note from the
`asimov@mac` host once and only once, and SHALL NOT carry orphan or duplicated fragments
of bullets already present on master.

#### Scenario: The three new notes are present once each

- **Given** the tree at the PR head
- **When** `tests/test_fleet_lifecycle.py::test_third_batch_host_ahead_implementer_notes_are_landed` reads `agents/tll-implementer/skills/tll-implementer/SKILL.md`
- **Then** each of the protected-instruction dispatch note, the `$GITHUB_EVENT_PATH` host-side gate note and the concurrent-writer collision note appears exactly once
- **Test:** tests/test_fleet_lifecycle.py::test_third_batch_host_ahead_implementer_notes_are_landed

#### Scenario: The orphan clause did not grow to a second copy

- **Given** master already owns the `BEFORE waiting on CI; doing this only after seeing the red` clause once
- **When** the same guard reads the head mirror
- **Then** that clause still appears once, so the duplicate defect from #1455/#1456/#1469 does not return
- **Test:** tests/test_fleet_lifecycle.py::test_third_batch_host_ahead_implementer_notes_are_landed
