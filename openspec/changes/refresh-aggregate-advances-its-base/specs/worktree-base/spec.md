# worktree-base

## ADDED Requirements

### Requirement: A job that has written nothing advances to the fetched tip

`worktree_base.py advance` MUST fast-forward a CLEAN checkout onto the fetched
base when HEAD is a strict ancestor of it, and report `advanced=<n>` and
`fresh=true`, so a CI job whose base moved during its own run still starts from
the tip instead of losing the run.

#### Scenario: the measured refresh shape

- **Given** a clone whose HEAD is one commit behind the fetched base, with a clean tree
- **When** `advance` runs
- **Then** it exits 0, HEAD IS the fetched tip, `advanced=1` is reported, and the base's content is in the tree
- **Test:** tests/test_worktree_base.py::test_advance_fast_forwards_a_checkout_behind_the_base

#### Scenario: a checkout that is already the tip

- **Given** a checkout that IS the freshly fetched base
- **When** `advance` runs
- **Then** it exits 0 and reports no advance
- **Test:** tests/test_worktree_base.py::test_advance_is_a_no_op_on_a_fresh_checkout

### Requirement: An advance never discards work

`advance` MUST refuse a dirty tree, and MUST refuse a HEAD carrying commits the
base does not have, naming what it found — the tip is reached, never assumed.

#### Scenario: a dirty tree

- **Given** an uncommitted file in the checkout
- **When** `advance` runs
- **Then** it exits 1, says the tree is dirty, and the file still exists
- **Test:** tests/test_worktree_base.py::test_advance_refuses_a_dirty_tree

#### Scenario: a diverged HEAD

- **Given** a HEAD with a commit the base does not have
- **When** `advance` runs
- **Then** it exits 1 with the STALE refusal reporting how many commits are ahead
- **Test:** tests/test_worktree_base.py::test_advance_refuses_a_head_with_its_own_commits

### Requirement: The advance is one seam reached through the Makefile

The mode MUST be reachable only through `make base-advance`, defined in the
Makefile and calling `scripts/worktree_base.py advance` (rules 6d/6m).

#### Scenario: the Makefile target

- **Given** the Makefile
- **When** the seam guard reads it
- **Then** `base-advance` exists and its recipe calls the `advance` mode
- **Test:** tests/test_worktree_base.py::test_the_makefile_is_the_one_seam
