# Capability: generated-artifact-repair

## ADDED Requirements

### Requirement: Repair keepers regenerate both generated artifacts

A post-merge repair job for a stale generated artifact SHALL regenerate BOTH the
`OPENSPEC.md` index and the `ARCHITECTURE.md` §10 inventory block before landing
its keeper, and the keeper SHALL name both files in its `FILE` set, so the resulting
keeper PR passes both generated gates (`openspec-index-check` and
`architecture-check`).

#### Scenario: index repair regenerates the sibling inventory block too

- **Given** a master merge left both the `OPENSPEC.md` index and the `ARCHITECTURE.md` block stale
- **When** the `index-repair` job classifies and regenerates the index
- **Then** it also regenerates the `ARCHITECTURE.md` block and lands one keeper naming both files
- **Test:** tests/test_complete_generated_keeper.py::test_index_repair_lands_both_generated_files

#### Scenario: architecture repair regenerates the sibling index too

- **Given** a master merge left both generated artifacts stale
- **When** the `architecture-repair` job classifies and regenerates the inventory block
- **Then** it also regenerates the `OPENSPEC.md` index and lands one keeper naming both files
- **Test:** tests/test_complete_generated_keeper.py::test_architecture_repair_lands_both_generated_files

#### Scenario: second keeper is a no-op after the first lands

- **Given** the first complete keeper already landed both regenerated files on master
- **When** the sibling repair job runs against the updated master
- **Then** `keeper_pr.py` finds no owned file changed and lands no second PR
- **Test:** tests/test_complete_generated_keeper.py::test_second_keeper_is_noop_when_both_current
