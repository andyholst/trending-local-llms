# worktree-base

## ADDED Requirements

### Requirement: A conflicted re-apply leaves no conflict marker

When the carried work conflicts with the branch it is re-applied onto, `mode_adopt` MUST keep
the run's side of every conflicted path, stage it, and leave NO `<<<<<<<` marker in the tree.
It MUST report the resolved paths as `merge_conflict=<path,…>`.

#### Scenario: the branch changed the same line the run changed

- **Given** a clone whose `f.txt` is modified by the run while the branch also changed it
- **When** `adopt` re-applies the stashed work
- **Then** `f.txt` holds the RUN's content, `git grep -l '^<<<<<<<'` is empty, and the output
  names `merge_conflict=f.txt`
- **Test:** tests/test_worktree_base.py::test_adopt_carries_uncommitted_work_onto_an_existing_branch

#### Scenario: an unresolvable path keeps its work in the stash

- **Given** a conflicted path the adopt cannot take a side for
- **When** the re-apply finishes
- **Then** the work stays in `git stash list` and the warning names the path
- **Test:** tests/test_worktree_base.py::test_adopt_carries_uncommitted_work_onto_an_existing_branch
