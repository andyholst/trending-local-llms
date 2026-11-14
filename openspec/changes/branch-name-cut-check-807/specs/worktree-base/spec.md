# worktree-base

## ADDED Requirements

### Requirement: A cut that declares its issue must name it, checked by the closure parser

When `make worktree-new` or `make branch-adopt` is given `ISSUE=<n>`, the seam MUST validate the
branch name through `scripts/pr_closure.py`'s own `implemented_issue` — the single parser rule 6e
defines — and MUST refuse (exit 1, before any worktree, branch or commit is created) when the name
resolves to a different issue or to no issue at all. The seam MUST NOT re-spell a branch-number
rule of its own.

#### Scenario: the measured #805 shape — a name the parser reads as another issue

- **Given** a clean checkout at the fetched base
- **When** `make worktree-new BRANCH=tech-debt-801-queued-alarm-window-933 ISSUE=801` runs
- **Then** it exits 1 naming BOTH issue numbers and the closure rule, and no branch or worktree exists
- **Test:** tests/test_worktree_base.py::test_new_with_issue_refuses_a_branch_naming_a_different_issue

#### Scenario: a name that implements nothing

- **Given** a clean checkout
- **When** `make worktree-new BRANCH=refresh-20261114T111522Z ISSUE=801` runs
- **Then** it is refused, naming that the branch resolves to NO issue
- **Test:** tests/test_worktree_base.py::test_new_with_issue_refuses_a_name_that_implements_nothing

#### Scenario: a name that declares what it implements is cut normally

- **Given** a clean checkout
- **When** `make worktree-new BRANCH=tech-debt-801-queued-alarm-window-801 ISSUE=801` runs
- **Then** it exits 0 and the worktree exists
- **Test:** tests/test_worktree_base.py::test_new_with_issue_accepts_the_name_it_declares

#### Scenario: a cut with no declaration is unchanged

- **Given** a descriptive branch name (keeper/refresh shape) and no `ISSUE=`
- **When** `make worktree-new BRANCH=refresh-20261114T111522Z` runs
- **Then** it exits 0 — the rule binds only a cut that declares an issue
- **Test:** tests/test_worktree_base.py::test_new_without_issue_leaves_descriptive_names_legal

#### Scenario: the check is THE parser, end to end, on the real branch shapes

- **Given** the four measured shapes (`ci/data-gap-1-x`, a matching trailing number, the #805
  mismatch, a refresh name)
- **When** the seam's check and `pr_closure.implemented_issue` are both run on each
- **Then** they agree on every one, and the seam imports the parser rather than defining its own
- **Test:** tests/test_worktree_base.py::test_the_cut_check_agrees_with_the_parser_on_the_real_shapes

### Requirement: An attach to an existing branch is never refused by the name rule

`make branch-adopt` MUST still attach a branch that already exists even when `ISSUE=` disagrees
with its name — the branch's name was validated when it was cut, and the #500 rescue path (a
re-run, and every branch cut before this rule) must stay open. A NEW branch cut by `adopt` IS
name-checked.

#### Scenario: the re-run's branch is attached, not refused

- **Given** a remote branch `ci/data-gap-1-x` and `ISSUE=999` on a re-run
- **When** `make branch-adopt BRANCH=ci/data-gap-1-x ISSUE=999` runs
- **Then** it attaches the branch (exit 0) and never prints the name refusal
- **Test:** tests/test_worktree_base.py::test_adopt_with_issue_still_attaches_an_existing_branch

#### Scenario: adopt's own new cut is checked before anything exists

- **Given** a dirty tree carrying this run's work and `ISSUE=801`
- **When** `make branch-adopt BRANCH=tech-debt-801-fix-933 ISSUE=801` runs
- **Then** it is refused, the branch was never created, and the work is still in the tree
- **Test:** tests/test_worktree_base.py::test_adopt_with_issue_refuses_a_mismatched_new_branch

### Requirement: `ISSUE=` belongs to the cut modes only, loudly

`--issue` on `base-check`, `resume` or `rebase` MUST be a usage error (exit 2) naming the modes it
belongs to; `--issue 0` MUST be refused, so a zero can never match a name that parses to nothing.

#### Scenario: resume is told where the knob lives

- **Given** any checkout
- **When** `make worktree-resume BRANCH=ci/data-gap-1-x ISSUE=1` runs
- **Then** it exits 2 naming `new/adopt`
- **Test:** tests/test_worktree_base.py::test_issue_belongs_to_the_cut_modes_only
