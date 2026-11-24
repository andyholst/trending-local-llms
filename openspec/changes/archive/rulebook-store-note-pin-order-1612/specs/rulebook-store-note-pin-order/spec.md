## ADDED Requirements

### Requirement: The #1395 provenance clause is pinned by presence and landing order, not by being last

`tests/test_agents_store_rows.py` SHALL assert that the §7b `Rule 3c note:` carries the
reviewer-approved `#1395` clause AND that the clause sits after its `#1209`/`#1232`/`#1258`
predecessors. It SHALL NOT require the clause to be the LAST one on the line: the note is a
shared append point, so later lanes (#1589, #1586) may append their clauses after it. A
bare substring check SHALL NOT satisfy this requirement — the order guarantee remains.

#### Scenario: Both approved landings pass the relaxed assertion

- **Given** the landed `AGENTS.md` §7b `Rule 3c note:` line
- **When** the pin reads it in Order A (`… #1395, #1589, #1586`) or in Order B
  (`… #1589, #1586, #1395`)
- **Then** both orders satisfy the presence + ascending-order predicate
- **Test:** tests/test_agents_store_rows.py::test_relaxed_note_accepts_both_landing_orders

#### Scenario: A missing or out-of-order #1395 clause still reds

- **Given** a note with the `#1395` clause deleted, or moved ahead of its `#1209` predecessor
- **When** the same predicate runs
- **Then** it returns False for both, so the module fails
- **Test:** tests/test_agents_store_rows.py::test_missing_or_out_of_order_1395_still_reds

#### Scenario: The brittle endswith pin does not come back

- **Given** this module's own source
- **When** it is read
- **Then** the assertion is made through `note_carries_clause_after_predecessors`, not an
  `endswith` call
- **Test:** tests/test_agents_store_rows.py::test_the_brittle_endswith_pin_is_gone_from_this_module
