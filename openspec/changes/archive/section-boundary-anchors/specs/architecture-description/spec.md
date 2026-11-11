# architecture-description

## ADDED Requirements

### Requirement: The architecture guard reads each section by a stable anchor

`scripts/architecture_check.py` MUST locate the regions of `ARCHITECTURE.md` and
`AGENTS.md` it is allowed to read by an HTML-comment anchor
(`<!-- arch:targets -->`, `<!-- arch:pipelines -->`, `<!-- arch:scripts -->`,
`<!-- arch:guards -->`, `<!-- agents:rulebook -->`, `<!-- agents:style -->`) and
never by a section number. `make architecture-check` MUST report every anchor a
document does not contain.

#### Scenario: a document that lost a boundary anchor is reported

- **Given** a fixture tree whose `ARCHITECTURE.md` has no `<!-- arch:scripts -->` anchor
- **When** `scripts/architecture_check.py` runs on it
- **Then** it reports that the document has no section-boundary anchor `<!-- arch:scripts -->`
- **Test:** `tests/test_architecture.py::test_a_lost_boundary_anchor_is_reported`

#### Scenario: restoring the anchor turns that finding green

- **Given** the same fixture tree, with the `<!-- arch:scripts -->` anchor restored
- **When** `scripts/architecture_check.py` runs on it
- **Then** no anchor finding is raised, and the §6 script-role check still reads that section
- **Test:** `tests/test_architecture.py::test_restoring_the_anchor_turns_the_finding_green`

#### Scenario: an anchor stranded away from any heading is reported

- **Given** a fixture whose `<!-- arch:guards -->` anchor sits inside the §6 table,
  with no section heading beside it
- **When** `scripts/architecture_check.py` runs on it
- **Then** it reports the anchor as having no section heading beside it
- **Test:** `tests/test_architecture.py::test_an_anchor_with_no_section_is_reported`

#### Scenario: renumbering a section does not repoint the guard

- **Given** a consistent fixture tree whose `ARCHITECTURE.md` sections are renumbered
  (`## 3.` becomes `## 5.`, `## 6.` becomes `## 9.`) while the anchors stay put
- **When** `scripts/architecture_check.py` runs on it
- **Then** it exits clean: the target tables and the §6 script roles are still read
- **Test:** `tests/test_architecture.py::test_a_renumbered_section_still_reads_the_right_tables`

### Requirement: Both documents carry every anchor the guard reads

`ARCHITECTURE.md` MUST carry all four `arch:` anchors beside their sections and
`AGENTS.md` MUST carry `<!-- agents:rulebook -->` beside §6b and
`<!-- agents:style -->` beside §7, so the guard's boundaries exist in the documents
it reads.

#### Scenario: the real repository's documents carry every anchor

- **Given** this repository after the change
- **When** `scripts/architecture_check.py` runs on it
- **Then** it exits 0 and both documents contain every anchor the guard names
- **Test:** `tests/test_architecture.py::test_the_real_documents_carry_every_anchor`

### Requirement: The test fixture builds the anchors the guard reads

The anchor list MUST live in one constant in `tests/test_architecture.py` that the
fixture tree uses to build its documents, so the guard, the fixture and the real
documents can never name different anchors.

#### Scenario: the fixture and the guard agree on the anchor spelling

- **Given** the fixture tree the suite builds
- **When** `scripts/architecture_check.py` runs on it
- **Then** it is clean in the anchor direction, and removing one of the constant's
  anchors from the fixture produces exactly the anchor finding
- **Test:** `tests/test_architecture.py::test_the_fixture_uses_the_anchors_the_guard_reads`
