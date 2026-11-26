# planner-skill-forward-merge Specification

## Purpose
TBD - created by archiving change planner-skill-ahead-1781. Update Purpose after archive.

## Requirements

### Requirement: The planner mirror carries the owner's forward clauses verbatim-once

The tracked planner skill SHALL contain each host-ahead owner clause exactly once, while every
line of the base mirror stays byte-identical — a derivative merge, never a wholesale copy.

#### Scenario: All five new clauses are present exactly once

- **Given** the tracked planner skill after this change
- **When** `tests/test_fleet_lifecycle.py::test_the_planner_mirror_carries_the_owner_style_and_pr_gate_notes` counts each new clause
- **Then** each needle is present and its count is one
- **Test:** tests/test_fleet_lifecycle.py::test_the_planner_mirror_carries_the_owner_style_and_pr_gate_notes

#### Scenario: The host's accidental base deletions are not copied

- **Given** a host copy that renamed `## Docs lane scope (owner-mandated)` and drifted `690/600s` to `660/600s`
- **When** the derivative merge lands
- **Then** the tracked mirror still carries the base heading and the base `690/600s` wording
- **Test:** tests/test_fleet_lifecycle.py::test_the_planner_mirror_carries_the_owner_style_and_pr_gate_notes
