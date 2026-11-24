## ADDED Requirements

### Requirement: The rulebook names the dispatch guard in §7b

`AGENTS.md` §7b SHALL carry one bold-led bullet stating that the planner runs `make dispatch-check`
before spawning a lane, and SHALL name every refusal class: a CLOSED issue, an issue whose bound PR is
already MERGED, a dispatch above the ONE active-lane ceiling (`ACTIVE_LANE_CEILING`, default 3), a
`--claim <repo-relative path>` overlapping a path another ACTIVE lane already holds, and a NEWER
active working-claim ANOTHER host holds on that issue's thread. The bullet SHALL also state the exit
contract: 0 allow, 1 refuse, 2 undecidable.

#### Scenario: A reader of §7b learns the four refusals

- **Given** `AGENTS.md` §7b
- **When** it is read
- **Then** it carries the dispatch-guard bullet naming `make dispatch-check`, `already MERGED`,
  `ACTIVE_LANE_CEILING`, `another ACTIVE lane` and `ANOTHER host`
- **Test:** tests/test_dispatch_guard.py::test_rulebook_section_7b_carries_the_dispatch_guard_bullet

#### Scenario: Deleting a single needle reds the pin

- **Given** the pinned §7b region with any one of the five needles removed
- **When** the pin function runs
- **Then** it reports exactly that missing needle and fails
- **Test:** tests/test_dispatch_guard.py::test_rulebook_section_7b_carries_the_dispatch_guard_bullet

### Requirement: §8 carries the dispatch-guard row

`AGENTS.md` §8 SHALL carry one regression-guard row naming `tests/test_dispatch_guard.py` and
`make dispatch-check`. The pin SHALL assert NAMES ONLY — the module name, `make dispatch-check` and
the issue ids — so rewording the row's prose keeps the pin green while deleting the row reds it.

#### Scenario: The §8 row is present and named

- **Given** `AGENTS.md` §8
- **When** the pin reads the first line naming `tests/test_dispatch_guard.py`
- **Then** that row also names `make dispatch-check`, `#1416` and `#1569`
- **Test:** tests/test_dispatch_guard.py::test_rulebook_section_8_carries_the_dispatch_guard_row

#### Scenario: Deleting the §8 row reds the suite

- **Given** an `AGENTS.md` whose §8 no longer carries the `tests/test_dispatch_guard.py` row
- **When** the pin function runs
- **Then** it fails with `AGENTS.md §8 dropped the dispatch guard row`
- **Test:** tests/test_dispatch_guard.py::test_rulebook_section_8_carries_the_dispatch_guard_row

### Requirement: The Rule 3c note records the dispatch-guard rule

The single `Rule 3c note:` line in §7b SHALL gain one clause recording that the dispatch-guard rule
was added by this issue and is review-required, appended at the END of that line after whichever
clause is last, so sibling landings (#1482, #1589) appending their own clauses are never overwritten.

#### Scenario: The note clause is present and ordered

- **Given** the `Rule 3c note:` line as landed
- **When** it is read
- **Then** it ends with the dispatch-guard clause for this issue and preserves every earlier clause
- **Test:** tests/test_dispatch_guard.py::test_rulebook_section_7b_carries_the_dispatch_guard_bullet
