## ADDED Requirements

### Requirement: A wrapped parenthetical aside is stripped whole

The union normaliser SHALL blank every BALANCED parenthetical group as a whole, including a
group that opens on one line and closes on a later line, so its inner clause contributes no
line or clause unit to the multiset. Newlines SHALL survive the mask so line units and line
structure are preserved.

#### Scenario: An aside that opens and closes across two lines

- **Given** a mirror bullet whose aside opens mid-line and closes on the following line
- **When** the union normaliser counts its lines and clauses
- **Then** the aside's inner clause contributes no unit, so a byte-equal mirror shows no growth
- **Test:** tests/test_fleet_lifecycle.py::test_a_wrapped_parenthetical_aside_is_stripped_whole

#### Scenario: An unmatched opener is not a licence to blank the file

- **Given** a parenthesis that opens and never closes
- **When** the mask runs
- **Then** that text is left exactly as written and its clause is still counted
- **Test:** tests/test_fleet_lifecycle.py::test_a_wrapped_parenthetical_aside_is_stripped_whole

### Requirement: Text outside the aside stays compared

Masking an aside SHALL NOT weaken the pin: a clause repeated OUTSIDE any parenthetical, or an
exact repeated bullet, is still detected as growth past the pinned base.

#### Scenario: A repeated clause outside any aside

- **Given** a clause already present at the pinned base
- **When** a new bullet repeats it outside every parenthetical
- **Then** the growth detector still fires
- **Test:** tests/test_fleet_lifecycle.py::test_a_wrapped_parenthetical_aside_is_stripped_whole

#### Scenario: A same-line aside keeps its old stripping

- **Given** a balanced parenthetical aside entirely on one line
- **When** the normaliser runs
- **Then** the aside is dropped exactly as before, with no regression
- **Test:** tests/test_fleet_lifecycle.py::test_a_wrapped_parenthetical_aside_is_stripped_whole
