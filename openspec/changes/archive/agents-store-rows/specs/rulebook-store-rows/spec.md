## ADDED Requirements

### Requirement: The rulebook carries #1395's declared store-architecture rows

`AGENTS.md` §7b SHALL name the store architecture page's two artifacts —
`ARCHITECTURE.md` §2 plus `docs/store.md` — and its `Rule 3c note` SHALL record that
those artifact names were added by issue #1395 and are review-required. `AGENTS.md` §8
SHALL carry one regression row for `tests/test_architecture.py`'s data-flow tests plus
`scripts/architecture_check.py::store_file_findings`, naming `data/models.json`,
`data/measurements.json` and `data/posts.json`. All three texts SHALL match the
reviewer-approved landing text on #1482 byte-for-byte.

#### Scenario: A reader checks which file owns the store walkthrough

- **Given** the landed `AGENTS.md`
- **When** a reader opens §7b's fleet paragraph
- **Then** it names both `ARCHITECTURE.md` §2 and `docs/store.md`
- **Test:** tests/test_agents_store_rows.py::test_section_7b_names_the_two_store_artifacts

#### Scenario: The provenance of the artifact names is recorded

- **Given** the landed `AGENTS.md`
- **When** a reader opens §7b's `Rule 3c note`
- **Then** it ends with the clause naming issue #1395 and keeps the earlier
  #1209/#1232/#1258 clauses
- **Test:** tests/test_agents_store_rows.py::test_rule_3c_note_records_the_1395_provenance

#### Scenario: The guard that backs the rows is discoverable from §8

- **Given** the landed `AGENTS.md`
- **When** a reader scans §8's regression-guard table
- **Then** exactly one row names `store_file_findings` and the three shipped store
  files, sitting beside its `tests/test_architecture.py` sibling
- **Test:** tests/test_agents_store_rows.py::test_section_8_carries_the_1395_regression_row
