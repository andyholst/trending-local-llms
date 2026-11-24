## ADDED Requirements

### Requirement: A brand-new unit repeated by a later union is flagged

The fleet-lifecycle guard SHALL flag a unit that is ABSENT at the pinned pre-union base yet
appears two or more times in the head tree (`base_count == 0 and head_n >= 2`), because a
note a later union invents twice is merge debris, not two distinct notes.

#### Scenario: An intra-line clause duplicated from nothing

- **Given** the pinned base carries none of a new note's clauses
- **When** a later union writes the same sentence twice inside ONE bullet
- **Then** the guard flags that clause with counts `0 -> 2`
- **Test:** tests/test_fleet_lifecycle.py::test_the_union_growth_detector_fires_on_a_planted_duplicate

#### Scenario: A whole repeated line invented from nothing

- **Given** the pinned base carries a bullet zero times
- **When** a later union appends that exact bullet as two lines
- **Then** the `line` unit count grows `0 -> 2` and the guard flags it
- **Test:** tests/test_fleet_lifecycle.py::test_the_union_growth_detector_fires_on_a_planted_duplicate

### Requirement: The new case cannot fire on a clause shared by two different bullets

A `clause` unit SHALL qualify for the absent-at-base case only when its repeats are
co-located inside ONE source line. A clause that occurs once in each of two DIFFERENT bullets
is legitimate prose and SHALL stay silent, preserving the existing `base_count > 0` rule for
cross-line recurrence.

#### Scenario: Two bullets legitimately ending on the same phrase

- **Given** the pinned base carries a closing phrase zero times
- **When** two different bullets each end on that same phrase
- **Then** the guard reports no `0 -> 2` growth for it
- **Test:** tests/test_fleet_lifecycle.py::test_the_union_growth_detector_fires_on_a_planted_duplicate

#### Scenario: A single clause repeated inside one bullet

- **Given** the pinned base carries a clause zero times
- **When** one bullet carries that clause twice
- **Then** the owner line holds both copies, so the guard flags it
- **Test:** tests/test_fleet_lifecycle.py::test_the_union_growth_detector_fires_on_a_planted_duplicate

### Requirement: The guard does not red its own shipped mirrors

The strengthened detector SHALL stay GREEN over the four real host-ahead mirrors at the head,
after the one genuine duplicate it exposes is removed, so a guard cannot ship while failing
its own tree.

#### Scenario: The real mirrors at head

- **Given** the four pinned mirrors read through real `git show` against the pinned base
- **When** the deduplicated reviewer mirror is compared
- **Then** every unit count is unchanged or `0 -> 1`, and the module exits 0
- **Test:** tests/test_fleet_lifecycle.py::test_mirror_unions_add_no_duplicate_or_interleaved_bullets
