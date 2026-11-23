## ADDED Requirements

### Requirement: A lane skill mirror carries no duplicated rule

A shipped `agents/<lane>/skills/<lane>/SKILL.md` mirror SHALL NOT carry the same
rule, sentence or list block twice. A union of master rules and host-ahead notes
SHALL keep each distinct note exactly once, whether the second copy came from a
merge splice, a doubled paragraph or a pre-existing repeat.

#### Scenario: A phrase the union repeated

- **Given** a mirror in which a non-trivial phrase appears more than once
- **When** the fleet-lifecycle guard reads the four mirrors
- **Then** it fails, naming the mirror and the repeated phrase
- **Test:** tests/test_fleet_lifecycle.py::test_second_batch_host_ahead_notes_are_landed

#### Scenario: A whole duplicated list block

- **Given** a mirror carrying two whitespace-equivalent top-level bullets
- **When** the guard reads the mirror
- **Then** it fails, naming the mirror and the duplicated block
- **Test:** tests/test_fleet_lifecycle.py::test_second_batch_host_ahead_notes_are_landed

#### Scenario: A dangling fragment after an issue reference

- **Given** a mirror whose line is a strict tail of another line once a trailing
  `(#NNNN)` reference is removed
- **When** the guard reads the mirror
- **Then** it fails as a duplicate rather than passing silently
- **Test:** tests/test_fleet_lifecycle.py::test_second_batch_host_ahead_notes_are_landed

### Requirement: De-duplication loses no genuine note

Removing a repeated copy SHALL NOT delete a line that appears exactly once at the
base revision or once in the host copy; the multiset of distinct rules is preserved.

#### Scenario: Base-only and host-only sentences survive

- **Given** the reconciled planner mirror
- **When** its text is compared with base `84cace0b` and the host copy
- **Then** every distinct sentence from either source is still present
- **Test:** tests/test_fleet_lifecycle.py::test_lane_skill_mirrors_carry_landed_host_ahead_notes
