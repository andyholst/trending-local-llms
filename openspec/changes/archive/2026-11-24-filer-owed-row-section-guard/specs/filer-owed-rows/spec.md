## ADDED Requirements

### Requirement: An explicit Owed-row field must name a real AGENTS.md section

The findings filer SHALL refuse an explicit `- **Owed-row:**` declaration whose section id is not
a `## <id>.` heading in `AGENTS.md`, through the SAME heading parser the ledger reads, BEFORE it
files anything. A filed issue therefore never carries a marker that makes `make owed-rows-check`
answer `NO SUCH SECTION` and exit 2.

#### Scenario: A rule number is not a section heading

- **Given** a findings file carrying `- **Owed-row:** <!-- owed-row: section=6r needle="make pipeline-failure-issue" -->`, where `6r` is a numbered rule inside `## 2.` and not a `## <id>.` heading
- **When** the real filer parses that analysis file
- **Then** it exits non-zero naming the unknown section and the known headings, and NO `gh issue create` call is made and no issue body is written
- **Test:** tests/test_filer_owed_rows.py::test_an_explicit_owed_row_section_that_is_not_a_heading_is_refused

#### Scenario: A real heading still files exactly one issue

- **Given** the same explicit field naming a heading that exists (`section=8`) with a guard-row identifier the text names
- **When** the real filer runs over that analysis file
- **Then** it exits 0, files exactly one issue, and the filed body carries the ONE registered marker re-rendered through `bot_markers.owed_row_marker`
- **Test:** tests/test_filer_owed_rows.py::test_an_explicit_owed_row_section_that_is_not_a_heading_is_refused

#### Scenario: The derivation path is unchanged

- **Given** a Done-when that names `§99z` (not a heading) or states no guard-row identifier
- **When** `owed_row_derive.derive_rows` runs over it
- **Then** it derives nothing, so the derived path can still never stamp a marker the ledger refuses
- **Test:** tests/test_filer_owed_rows.py::test_the_derivation_states_only_what_the_text_names
