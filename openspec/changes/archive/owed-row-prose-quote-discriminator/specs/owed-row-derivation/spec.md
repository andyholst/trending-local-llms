# owed-row-derivation Specification

## MODIFIED Requirements

### Requirement: A marker quoted in prose is not a declaration

`bot_markers.parse_owed_rows` SHALL register an `owed-row` marker only where the thread DECLARES
it, and SHALL NOT register one that QUOTES a marker. Before the unchanged grammar runs, the reader
strips every quotation device GitHub markdown renders as code — a fenced code block (``` ``` ``` or
`~~~`), an inline code span (`` `…` `` on one line) and a block-quoted line (`> …`) — so a comment
discussing another issue's marker cannot mint a row on its own thread.

A genuine declaration stays reachable: `- **Owed-row:** <marker>` written on an issue body or in a
`findings/*.md` file (the shape `scripts/file_findings.py` stamps) carries no quotation device, so
it still registers, exactly once.

#### Scenario: The recorded #1685 thread declares exactly one row

- **Given** the recorded #1685 thread (`tests/fixtures/thread_1685_quoted_markers.txt`), whose body carries one `- **Owed-row:** section=8 needle=test_a_planted_json_projection_path_is_refused` and whose comments quote that marker twice inline and quote #1581's `section=6r` marker inside a design comment
- **When** `bot_markers.parse_owed_rows` reads it
- **Then** it answers exactly one row (`section=8`, that needle), with NO `section=6r` row and nothing in `malformed`
- **Test:** tests/test_bot_markers.py::test_a_marker_quoted_in_prose_is_not_a_declaration

#### Scenario: Each quotation device on its own

- **Given** a thread carrying one marker inside an inline code span, one inside a fenced code block and one on a block-quoted line, and no unquoted declaration
- **When** `parse_owed_rows` reads it
- **Then** it answers no rows at all — each device is stripped, not just the one the defect measured
- **Test:** tests/test_bot_markers.py::test_a_marker_quoted_in_prose_is_not_a_declaration

#### Scenario: A findings-style declaration still registers

- **Given** a findings-style body ending in an unquoted `- **Owed-row:** <marker>` for `section=8`
- **When** `parse_owed_rows` reads it
- **Then** the row registers with its exact section and needle and `malformed` is empty
- **Test:** tests/test_bot_markers.py::test_a_genuine_findings_style_declaration_still_registers

#### Scenario: #1581's own malformed item is still reported, its fenced proposal is not

- **Given** the recorded #1581 thread (`tests/fixtures/thread_1581_quoted_markers.txt`), whose issue BODY carries `- **Owed-row:** <!-- owed-row: section=6r needle="make pipeline-failure-issue" -->` UNQUOTED and whose design comment shows two further markers inside a fenced EXAMPLE of a proposed edit
- **When** `parse_owed_rows` reads it
- **Then** the `section=6r` row is still REPORTED (so `make owed-rows-check` keeps answering `NO SUCH SECTION` for #1581 — its repair stays #1581's body edit), and NO row from the fenced proposal appears
- **Test:** tests/test_bot_markers.py::test_the_pre_existing_1581_section_6r_item_is_still_reported

#### Scenario: The live ledger loses the phantom rows

- **Given** the repository at the PR head and GitHub readable
- **When** `make owed-rows-check REPO=andyholst/trending-local-llms` runs
- **Then** no `#1685 section=6r` line is printed, exactly one `#1685 section=8` line is printed, and the summary's `problems` count drops by 3 relative to the unfixed parser on the same base (measured: 4 → 1; the remaining problem is #1581's own item). Six open threads changed match counts at all (#1486 3→1, #1581 4→1, #1667 2→1, #1685 4→1, #1687 2→1, #1690 2→0) and every dropped marker was read in its own context as quoted
- **Test:** tests/test_bot_markers.py::test_a_marker_quoted_in_prose_is_not_a_declaration
