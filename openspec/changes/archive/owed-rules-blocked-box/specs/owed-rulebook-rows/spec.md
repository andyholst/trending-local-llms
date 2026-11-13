## ADDED Requirements

### Requirement: An owed rulebook row is blocked-and-declared, never a bare box

A headless implementation leg REFUSED the write to the protected `AGENTS.md`
SHALL write the owed `tasks.md` box AT CREATION as
`- [~] … — blocked: rule 3c human sign-off …` (green-but-review-required) and
SHALL record the FULL row text as a `findings.md` finding carrying an
`- **Owed-row:**` declaration. The implementer's preloaded skill SHALL state
this contract, and a bare `- [ ]` for an owed rulebook row SHALL be treated as
the defect it is.

#### Scenario: The implement leg's contract forbids the bare box

- **Given** the `issue-implement` skill the implement recipe preloads
- **When** its contract text is read
- **Then** it forbids a bare `- [ ]` for an owed rulebook row, teaches the
  blocked box written at creation (`- [~] … blocked: rule 3c human sign-off`),
  and routes the row text through `make file-findings` to `make owed-rows-check`
- **Test:** tests/test_workflows.py::test_the_implement_leg_never_leaves_an_owed_rulebook_row_bare

### Requirement: `findings.md` carries the owed-row declaration through the registered grammar

An optional `- **Owed-row:**` field in a finding SHALL be validated through
`scripts/bot_markers.parse_owed_rows` (ONE grammar, rule 6j). A field that
declares nothing valid — plain prose without the marker, or a marker missing
`section=`/`needle=` — SHALL fail `make findings-check` loudly, naming the
finding and the expected grammar. A findings file without the field SHALL stay
valid (the field is optional; rule 3b — additive only).

#### Scenario: A valid Owed-row field parses into a row declaration

- **Given** a finding whose `- **Owed-row:**` line carries
  `<!-- owed-row: section=8 needle="owed rulebook row" -->`
- **When** `scripts/file_findings.py` parses it (`--check`)
- **Then** the parse is green and the finding holds the row
  `{section: "8", needle: "owed rulebook row"}`
- **Test:** tests/test_file_findings.py::test_an_owed_row_finding_files_the_registered_marker

#### Scenario: A half-written Owed-row field fails loudly

- **Given** a findings file whose Owed-row field is plain prose, and another
  whose marker carries no `needle=`
- **When** `make findings-check` runs on each
- **Then** both fail non-zero, naming the finding and the owed-row grammar, and
  a findings file with NO Owed-row field still parses green
- **Test:** tests/test_file_findings.py::test_an_owed_row_field_that_declares_nothing_fails_loudly

### Requirement: The filed ledger issue carries the marker written by the ONE writer

When a finding carries a valid owed-row declaration, the issue filed by
`make file-findings` SHALL contain the declaration RE-RENDERED through
`scripts/bot_markers.owed_row_marker` (no second writer, rule 6j/6d), beside
the `tech-debt-signature` dedup marker — so `make owed-rows-check` reports the
row LANDED or OUTSTANDING without re-reading a thread.

#### Scenario: The filed body carries both registered markers

- **Given** a finding with a valid Owed-row declaration, filed through the real
  script with `gh` stubbed (external system only, rule 6m)
- **When** the filed body is read
- **Then** it contains `<!-- owed-row: section=8 needle="owed rulebook row" -->`
  exactly as `owed_row_marker` renders it, and the dedup signature
- **Test:** tests/test_file_findings.py::test_an_owed_row_finding_files_the_registered_marker
