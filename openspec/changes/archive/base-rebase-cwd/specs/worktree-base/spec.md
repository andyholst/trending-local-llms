## ADDED Requirements

### Requirement: A rebase refuses a checkout that is not the named branch

`worktree_base.mode_rebase` SHALL refuse, loudly and without rebasing, when the current
HEAD is not the named branch, because the head it reads is `HEAD` and a report about a
different branch is a silent no-op.

#### Scenario: A rebase invoked from another checkout is refused

- **Given** a worktree on `master` and a branch 29 commits behind the fetched base
- **When** `mode_rebase` runs with that branch named
- **Then** it refuses, naming the checkout's HEAD and the remedy, and never prints `rebase=up-to-date`
- **Test:** tests/test_worktree_base.py::test_a_rebase_from_another_checkout_is_refused

#### Scenario: The branch's own worktree still reports the truth

- **Given** the branch checked out in its own worktree
- **When** `mode_rebase` runs with the same branch named
- **Then** it reports the true `behind_base` and rebases or reports the conflict
- **Test:** tests/test_worktree_base.py::test_a_rebase_from_the_branch_worktree_reports_the_true_behind_base
