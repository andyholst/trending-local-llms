## ADDED Requirements

### Requirement: The mirror union is compared against a pinned pre-union base

The fleet-lifecycle guard SHALL compare each of the four host-ahead mirrors against ONE
pinned base revision (`84cace0b38f4667eb55a7edfa1466c59ac1cec00`) as a MULTISET of
non-trivial lines and clauses, and SHALL fail when any unit already present at the base
appears MORE times in the head tree. A unit absent at the base is a legitimate new note.

#### Scenario: A clause duplicated by a later union

- **Given** the planner mirror carries `Enforce BOTH halves mechanically BEFORE` once at the pinned base
- **When** a union interleaves a second copy into another bullet
- **Then** the guard fails, naming the mirror, the unit kind and the counts `1 -> 2`
- **Test:** tests/test_fleet_lifecycle.py::test_mirror_unions_add_no_duplicate_or_interleaved_bullets

#### Scenario: A dangling fragment repeated inside a sentence

- **Given** the implementer mirror ends a bullet with `chasing it (#972).` at the pinned base
- **When** a union appends a bare second `chasing it.` line
- **Then** the parenthetical-insensitive clause count grows `1 -> 2` and the guard fails
- **Test:** tests/test_fleet_lifecycle.py::test_mirror_unions_add_no_duplicate_or_interleaved_bullets

#### Scenario: A purely additive note

- **Given** a mirror at the pinned base
- **When** a new note is added that repeats no existing line or clause
- **Then** every unit count is unchanged or `0 -> 1`, and the guard passes
- **Test:** tests/test_fleet_lifecycle.py::test_the_union_growth_detector_fires_on_a_planted_duplicate

#### Scenario: An unreadable pinned base is loud, never vacuous

- **Given** `git show <base>:<mirror>` cannot be read or answers empty
- **When** the guard runs
- **Then** it fails naming the mirror and the pinned sha, instead of comparing two empty strings
- **Test:** tests/test_fleet_lifecycle.py::test_mirror_unions_add_no_duplicate_or_interleaved_bullets

### Requirement: Every landed host-ahead note is carried exactly once

For each of the four mirrors, the guard SHALL assert that each landed note needle is
present AND appears exactly once, so a union cannot grow a landed note to two copies while
the presence check stays green.

#### Scenario: A landed note duplicated by a union

- **Given** the planner mirror carries `Verify a landed change against \`origin/master\`` once
- **When** a union adds a second copy of that bullet
- **Then** the exactly-once assertion fails
- **Test:** tests/test_fleet_lifecycle.py::test_second_batch_host_ahead_notes_are_landed

#### Scenario: A landed note present exactly once

- **Given** a deduplicated mirror
- **When** the guard runs
- **Then** every landed-note needle reports one copy
- **Test:** tests/test_fleet_lifecycle.py::test_second_batch_host_ahead_notes_are_landed

### Requirement: The detector is RED-first on a planted duplicate

The guard SHALL prove its own detector fires on a planted duplicate and an interleaved
repeat, and stays silent on a pure addition, using real text rather than a stand-in for the
comparison logic.

#### Scenario: The three detector shapes

- **Given** a small real bullet block
- **When** a purely additive line, an exact repeated bullet and an interleaved repeated clause are each compared against it
- **Then** only the additive case produces no growth, and both duplicate shapes do
- **Test:** tests/test_fleet_lifecycle.py::test_the_union_growth_detector_fires_on_a_planted_duplicate
