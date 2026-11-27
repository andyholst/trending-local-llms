## ADDED Requirements

### Requirement: A generated-only conflict with an advanced master is classified as retryable

The merge-tree step SHALL capture the unmerged paths before `git merge --abort` and
pass them, with the real `git merge-base HEAD origin/master` and
`git rev-parse origin/master` SHAs, to the ONE pure classifier reached only through
`make merge-tree-index-classify`. The classifier SHALL return `GENERATED_ADVANCE`
only when every captured path is `OPENSPEC.md` and the two SHAs differ.

#### Scenario: Generated index conflict after master advanced

- **Given** unmerged paths `OPENSPEC.md` and `base_before != master_after`
- **When** the real classifier runs through the real make target
- **Then** it prints exactly `GENERATED_ADVANCE`, and the step re-reads origin/master, regenerates the generated index with `make openspec-index`, stages it, re-runs the unchanged `make openspec-index-check`, emits `[merge-tree-index] MASTER-ADVANCE-RETRY` and exits 0
- **Test:** tests/test_openspec_merge_tree_check.py::test_generated_advance_conflict_gets_a_distinct_retryable_verdict

### Requirement: Any real conflict keeps the original hard failure

A non-generated conflicting path, an empty path set, or a generated conflict with no
master advance SHALL classify as `REAL_CONFLICT`, and the step SHALL keep the exact
`[merge-tree-index] MERGE CONFLICT` line and `exit 1`.

#### Scenario: A generated path plus a source file conflicts

- **Given** unmerged paths `OPENSPEC.md,scripts/x.py`
- **When** the real classifier runs
- **Then** it prints `REAL_CONFLICT` and the step keeps `[merge-tree-index] MERGE CONFLICT` with `exit 1`
- **Test:** tests/test_openspec_merge_tree_check.py::test_real_conflict_still_fails

#### Scenario: A generated conflict without a master advance is not a race

- **Given** unmerged paths `OPENSPEC.md` and `base_before == master_after`
- **When** the real classifier runs
- **Then** it prints `REAL_CONFLICT`, never `GENERATED_ADVANCE`
- **Test:** tests/test_openspec_merge_tree_check.py::test_a_generated_conflict_without_a_master_advance_is_not_a_race

### Requirement: The #1239 gate is never skipped or weakened

A clean merge whose index is stale SHALL still run the UNCHANGED
`make openspec-index-check` on the merged tree and fail with `[merge-tree-index] FAIL`.
All original #1239 clauses, the full-history fetch precondition and the PR-head
`make openspec-check` gate SHALL remain byte-present, and `git reset --hard HEAD`
SHALL restore the tree on every exit path.

#### Scenario: Clean merge with a stale index

- **Given** a clean merge of master into the PR head and a stale index
- **When** the step runs
- **Then** `make openspec-index-check` runs unchanged and the step fails with `[merge-tree-index] FAIL`
- **Test:** tests/test_openspec_merge_tree_check.py::test_clean_merge_stale_index_still_fails

#### Scenario: Every preserved clause survives

- **Given** the current `qa-validate` workflow
- **When** the guard module scans the merge-tree step
- **Then** all eight original #1239 clauses are present, the seam is wired to a make target and this suite is discovered by `make test`
- **Test:** tests/test_openspec_merge_tree_check.py::test_all_1239_clauses_survive
