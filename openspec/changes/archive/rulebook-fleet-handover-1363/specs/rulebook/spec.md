# rulebook

## ADDED Requirements

### Requirement: The §8 fleet-handover row names the landed generated-artifact guard

`AGENTS.md` §8's row for `tests/test_fleet_handover_protocol.py` MUST name the #1361
generated-artifact guard `test_pr_rebase_soul_names_the_generated_artifact_pair` together with
its issue and PR (#1361/#1362), so the guard has a reviewable rulebook home. The row MUST keep
its two-cell table shape and MUST stay exactly one row — the existing row is EXTENDED in place,
never duplicated.

#### Scenario: the row is present

- **Given** `AGENTS.md` at the landing head
- **When** the guard reads §8
- **Then** exactly one row names `tests/test_fleet_handover_protocol.py` and it carries
  `test_pr_rebase_soul_names_the_generated_artifact_pair`, `#1361`, `#1362` and keeps the
  two-cell table shape
- **Test:** tests/test_fleet_handover_protocol.py::test_section_8_row_names_the_1361_generated_artifact_guard

#### Scenario: dropping the name turns the suite red

- **Given** the landing head with the generated-artifact guard name removed from the §8 row
- **When** the module runs
- **Then** it exits 1 naming the dropped guard name, issue and PR
- **Test:** tests/test_fleet_handover_protocol.py::test_section_8_row_names_the_1361_generated_artifact_guard
