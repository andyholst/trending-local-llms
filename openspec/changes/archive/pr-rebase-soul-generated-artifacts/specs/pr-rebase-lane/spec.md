## ADDED Requirements

### Requirement: The rebase lane's conflict list names the generated artifacts

`agents/tll-pr-rebase/SOUL.md` SHALL name `OPENSPEC.md` and `ARCHITECTURE.md` §10 in
its habitual-conflict list, with the same regenerate-never-hand-merge rule `README.md`
already carries, so a branch that conflicts only on a stale generated count line is
resolved instead of stopped on.

#### Scenario: The generated pair is in the list

- **Given** the lane's SOUL on the branch
- **When** the guard reads its habitual-conflict list
- **Then** both `OPENSPEC.md` and `ARCHITECTURE.md` appear in that list
- **Test:** tests/test_fleet_handover_protocol.py::test_pr_rebase_soul_names_the_generated_artifact_pair

#### Scenario: The regenerate commands are named

- **Given** the lane's SOUL on the branch
- **When** the guard reads its habitual-conflict list
- **Then** `make openspec-index` and `make architecture-refresh` are named as the
  resolution for the generated pair
- **Test:** tests/test_fleet_handover_protocol.py::test_pr_rebase_soul_names_the_generated_artifact_pair
