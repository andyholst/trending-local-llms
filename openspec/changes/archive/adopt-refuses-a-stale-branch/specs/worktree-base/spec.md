# worktree-base

## ADDED Requirements

### Requirement: Adopt refuses a branch that is not this run's work

`mode_adopt` MUST refuse (exit 1, `REFUSED:` on stderr) to adopt an existing branch that carries
more than `RESUME_MAX_AHEAD` commits the base does not have, BEFORE it stashes, checks out or
otherwise touches the tree. The message MUST name the branch, both counts and the remedy. Passing
`--resume-stale` MUST adopt it anyway.

#### Scenario: an abandoned branch is refused and the tree is untouched

- **Given** a branch carrying 5 commits the base does not have, a dirty tree holding the run's work,
  and `RESUME_MAX_AHEAD=2`
- **When** `adopt --branch <that branch>` runs
- **Then** it exits 1, names the branch and `5 commit(s)`, the working file still holds the run's
  content, HEAD has not moved and `git stash list` is empty
- **Test:** tests/test_worktree_base.py::test_adopt_refuses_a_branch_that_is_not_this_runs_work

#### Scenario: the override adopts it

- **Given** the same branch and a dirty tree
- **When** `adopt --branch <that branch> --resume-stale` runs
- **Then** it exits 0 and reports `how=existing-remote`
- **Test:** tests/test_worktree_base.py::test_adopt_refuses_a_branch_that_is_not_this_runs_work

#### Scenario: a re-run's own branch is still adopted

- **Given** a branch carrying this run's single commit
- **When** `adopt --branch <that branch>` runs with the same threshold
- **Then** it exits 0 and reports `how=existing-remote`
- **Test:** tests/test_worktree_base.py::test_adopt_still_resumes_a_reruns_own_branch
