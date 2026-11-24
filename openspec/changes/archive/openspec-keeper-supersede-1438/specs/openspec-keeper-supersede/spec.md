## ADDED Requirements

### Requirement: A behind index-repair keeper is classified SUPERSEDED

The ONE keeper dedupe (`scripts/keeper_pr.py`) SHALL classify an OPEN, MERGEABLE
keeper on its branch prefix as SUPERSEDED when the `archived:` count in its head
`OPENSPEC.md` is BELOW the count in `origin/master`. A keeper at or above the
master count SHALL NOT be classified SUPERSEDED.

#### Scenario: A stale mergeable keeper

- **Given** an open mergeable keeper whose head index says `archived: **397**`
- **When** the dedupe runs against a master index saying `archived: **486**`
- **Then** the keeper is classified SUPERSEDED and named with both counts
- **Test:** tests/test_keeper_pr.py::test_a_stale_mergeable_index_repair_keeper_is_superseded_and_closed

#### Scenario: A current mergeable keeper

- **Given** an open mergeable keeper whose head index matches the master count
- **When** the dedupe runs
- **Then** it stays LIVE and suppresses a duplicate exactly as before
- **Test:** tests/test_keeper_pr.py::test_a_current_mergeable_index_repair_keeper_is_live

### Requirement: A SUPERSEDED keeper is closed with its count evidence

A SUPERSEDED keeper SHALL be closed without a rebase or force-push, carrying ONE
comment with the keeper count and the master count. Closing removes it from the
OPEN set, so a re-run cannot comment twice; a close that fails is reported, never
silent.

#### Scenario: The stale keeper is closed and a fresh one still lands

- **Given** a SUPERSEDED keeper on the prefix and a real drift to land
- **When** `make keeper-pr --dedupe` runs
- **Then** the stale keeper is commented and closed, and a FRESH keeper branch is pushed
- **Test:** tests/test_keeper_pr.py::test_a_stale_mergeable_index_repair_keeper_is_superseded_and_closed

### Requirement: The classifier is proven RED on the pre-change seam

The guard SHALL fail against the pre-change `scripts/keeper_pr.py`, so the
SUPERSEDED behaviour is demonstrably new.

#### Scenario: The base revision has no classifier

- **Given** `git show origin/master:scripts/keeper_pr.py` (no SUPERSEDED path)
- **When** the module's own checks run against it
- **Then** they fail, naming the missing classification
- **Test:** tests/test_keeper_pr.py::test_the_supersede_guard_is_red_on_the_base_revision
