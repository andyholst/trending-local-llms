## ADDED Requirements

### Requirement: Merge-tree index verification

The validate job SHALL verify the generated OpenSpec index on the tree produced by
merging current master into the PR head, in addition to the existing PR-head check. A
merge conflict SHALL fail loudly with a rebase instruction; a stale index SHALL fail
with the `make openspec-index` repair instruction; the checked-out tree SHALL be
restored before the next step.

#### Scenario: Two PRs regenerate the index from different bases

- **WHEN** a PR merges after a sibling that also archived a change
- **THEN** the merge-tree `make openspec-index-check` fails on the PR before merge
- **AND** the PR must regenerate the index and rebase before it can merge

#### Scenario: Guard removed

- **WHEN** the merge-tree step or its restore is removed from the workflow
- **THEN** `tests/test_openspec_merge_tree_check.py` fails with a named finding
