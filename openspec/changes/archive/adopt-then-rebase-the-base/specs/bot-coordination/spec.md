# bot-coordination

## ADDED Requirements

### Requirement: The implementer adopts a branch instead of re-asserting its base

At commit time the implementer MUST create or attach its branch from the current HEAD without
asserting that HEAD is the fetched base tip, and MUST report how far behind the base it is; a branch
that already exists MUST be attached, never re-cut.

#### Scenario: the base moved while the agent worked

- **Given** a checkout 1 commit behind the fetched base and an uncommitted implementation
- **When** `make branch-adopt BRANCH=ci/data-gap-2-x` runs
- **Then** it exits 0, cuts the branch from HEAD, reports `behind_base=1`, and the work is still in the tree
- **Test:** tests/test_worktree_base.py::test_adopt_cuts_the_branch_from_a_behind_head_and_keeps_the_work

#### Scenario: a re-run resumes its branch

- **Given** a branch that already exists on the remote
- **When** `make branch-adopt` runs
- **Then** it attaches that branch (`how=existing-remote`) instead of re-cutting it
- **Test:** tests/test_worktree_base.py::test_adopt_attaches_an_existing_branch_instead_of_recutting_it

### Requirement: The commit is rebased onto the fetched tip, and a conflict never loses it

After the commit and before the push the implementer MUST rebase onto the fetched base; a conflict
MUST abort the rebase, leave every commit intact, report exit 3, and let the push proceed.

#### Scenario: behind and clean

- **Given** a committed branch behind the fetched base
- **When** `make base-rebase` runs
- **Then** it rebases, and the base tip is an ancestor of HEAD
- **Test:** tests/test_worktree_base.py::test_rebase_brings_the_commit_onto_the_fetched_tip

#### Scenario: a conflict

- **Given** a branch whose commit touches the same lines as a new base commit
- **When** `make base-rebase` runs
- **Then** it exits 3, prints `rebase=conflict` and the conflicted path, and HEAD is unchanged with no rebase in progress
- **Test:** tests/test_worktree_base.py::test_rebase_conflict_keeps_every_commit_and_says_exit_3

#### Scenario: uncommitted changes

- **Given** a dirty tree
- **When** `make base-rebase` runs
- **Then** it is REFUSED, so a rebase never moves work it cannot see
- **Test:** tests/test_worktree_base.py::test_rebase_refuses_a_tree_with_uncommitted_changes

### Requirement: A finished implementation is never lost to a rejected push

The implementer's commit step MUST call no base-asserting target, MUST rebase before the push, and
MUST upload the implementation as a patch artifact on any rejected push.

#### Scenario: the step's own wiring

- **Given** `issue-bot.yml`'s commit step
- **When** the guard reads it
- **Then** it calls `make branch-adopt` and `make base-rebase` (before the push), calls no `worktree-new`/`worktree-resume`/`base-check`, and the patch artifact is not gated on the workflow-scope error
- **Test:** tests/test_worktree_base.py::test_the_makefile_is_the_one_seam
