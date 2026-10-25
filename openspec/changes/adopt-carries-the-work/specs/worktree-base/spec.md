# worktree-base

## ADDED Requirements

### Requirement: Adopting an existing branch carries uncommitted work

`mode_adopt` MUST NOT refuse a dirty working tree when the branch already exists locally or
on the remote: it MUST stash the work, attach the branch, and re-apply the work, keeping it
in the tree (cleanly or as conflict markers) and never discarding it.

#### Scenario: a re-run with a dirty tree and an existing remote branch

- **Given** a clone on `master` with a dirty `f.txt` (the file the remote branch changed), a new file and an untracked file
- **When** `adopt --branch ci/data-gap-1-x` runs
- **Then** it exits 0, reports `how=existing-remote-reapplied`, HEAD is that branch, the branch's earlier commit is intact, and the work is still present
- **Test:** tests/test_worktree_base.py::test_adopt_carries_uncommitted_work_onto_an_existing_branch

#### Scenario: a conflicting re-apply is reported, not swallowed

- **Given** the same tree where the change touches the line the branch changed
- **When** the stash is re-applied
- **Then** the work is kept (markers and/or the stash entry) and `merge_conflict=true` is printed
- **Test:** tests/test_worktree_base.py::test_adopt_carries_uncommitted_work_onto_an_existing_branch

#### Scenario: a first run is unchanged

- **Given** no branch by that name, with uncommitted work
- **When** `adopt` runs
- **Then** it reports `how=cut-from-head` and the work is untouched (issue #500 behaviour)
- **Test:** tests/test_worktree_base.py::test_adopt_cuts_the_branch_from_a_behind_head_and_keeps_the_work
