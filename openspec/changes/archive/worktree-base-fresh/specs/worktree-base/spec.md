# worktree-base

## ADDED Requirements

### Requirement: The base is fetched and asserted, never assumed

Every implementation MUST start from a working copy whose base commit is the **freshly
fetched** tip of the upstream base branch (`origin/master`), and the base MUST be
asserted rather than assumed: a run that cannot fetch the base, or whose checkout is not
the fetched tip, MUST fail loudly and name both commits. A fresh CI checkout is the
latest `origin/master` only by accident of the runner, so it is asserted like any other.
The fetch, the assertion and the refusal have exactly ONE implementation, reachable from
a `make` target CI runs (rules 6d/6m).

WHEN a run asserts its base,
THEN it fetches the base branch first, and either the checkout's HEAD equals the fetched
tip or the run exits non-zero naming the checkout's commit and the fetched tip.

#### Scenario: a checkout behind the fetched base fails loudly

- **Given** a clone of a repository whose base branch has moved on the remote since the clone
- **When** the base is asserted
- **Then** the run exits 1 and names both the checkout's commit and the fetched tip
- **Test:** `tests/test_worktree_base.py::test_check_fails_on_a_checkout_behind_the_fetched_base`

#### Scenario: a base that cannot be fetched never passes

- **Given** a checkout whose remote cannot be reached
- **When** the base is asserted
- **Then** the run exits non-zero with the fetch failure, and never reports a fresh base
- **Test:** `tests/test_worktree_base.py::test_check_fails_loudly_when_the_fetch_fails`

#### Scenario: the pipelines assert the base they cut from

- **Given** the pipeline that cuts an implementation branch off `master`
- **When** it starts an implementation
- **Then** it runs `make base-check` through the Makefile before anything is implemented
- **Test:** `tests/test_workflows.py::test_issue_bot_asserts_the_base_it_cuts_from`

### Requirement: A new implementation starts in a worktree off that base

Starting a new implementation MUST create the branch at the fetched base tip, in a
**worktree** on the local path (so one clone cannot serve two overlapping implementations
through a shared, dirty tree) and in place in CI (where the fresh checkout already is
that isolated copy). It MUST refuse a branch that already exists rather than re-cut it —
re-cutting discards commits — and MUST refuse a worktree created inside the repository,
where a `git add -A` would sweep it into someone's commit.

WHEN a new branch is started,
THEN a worktree (or the CI checkout) exists on that branch at the fetched base tip, and
the run reports the branch, its base and its path.

#### Scenario: the worktree is created at the fetched tip, not at the clone's old tip

- **Given** a clone-of-a-clone whose remote advanced after the clone was taken
- **When** a new branch is started
- **Then** the new worktree's HEAD is the fetched tip and the run reports it
- **Test:** `tests/test_worktree_base.py::test_new_creates_a_worktree_at_the_fetched_tip`

#### Scenario: an existing branch is refused, never re-cut

- **Given** a branch that exists on the remote
- **When** a new branch is started under that name
- **Then** the run exits 1 and points at the resume path instead of resetting the branch
- **Test:** `tests/test_worktree_base.py::test_new_refuses_an_existing_branch`

#### Scenario: a worktree inside the repository is refused

- **Given** a requested worktree directory inside the repository root
- **When** a new branch is started
- **Then** the run exits 1, because a `git add -A` in the repository would commit it
- **Test:** `tests/test_worktree_base.py::test_new_refuses_a_worktree_inside_the_repo`

#### Scenario: the checkout the caller stands on is never disturbed

- **Given** a checkout standing on the base branch, with local branches of its own
- **When** a worktree is created
- **Then** the caller's HEAD, the branch it stands on and the local base branch are all
  exactly as they were — the worktree is cut from `refs/remotes/<remote>/<base>`, never
  from or through the local base branch, and the base branch itself is refused as a target
- **Test:** `tests/test_worktree_base.py::test_new_never_touches_the_checkout_the_caller_stands_on`

#### Scenario: the base branch is never a worktree target

- **Given** a request to start or resume `master` itself
- **When** the decision is evaluated
- **Then** the run exits 1: work happens on a branch OFF the base, and the base is never
  checked out anywhere
- **Test:** `tests/test_worktree_base.py::test_new_and_resume_refuse_the_base_branch_itself`

### Requirement: An existing branch is resumed by fetching it first

Resuming an implementation (a re-run) MUST fetch the branch from the remote before
attaching to it, and MUST report how far the branch is behind the fetched base, so drift
is visible instead of silent. A resume MUST NOT discard commits that exist only locally.

WHEN an existing branch is resumed,
THEN it is fetched from the remote, attached, and the run reports the branch's commit and
its distance behind the base.

#### Scenario: a single-ref clone can resume the branch

- **Given** a clone fetched with one ref (`ref: master`, the shape `actions/checkout` leaves)
- **When** the branch is resumed
- **Then** the resume succeeds with the branch's remote commit checked out, where a bare
  `git checkout <branch>` fails with `pathspec … did not match`
- **Test:** `tests/test_worktree_base.py::test_resume_works_where_a_bare_checkout_fails`

#### Scenario: a branch behind the base says so

- **Given** a branch cut before the base branch gained a commit
- **When** the branch is resumed
- **Then** the run reports `behind_base=` with the number of base commits the branch lacks
- **Test:** `tests/test_worktree_base.py::test_resume_reports_how_far_behind_the_base_it_is`

#### Scenario: local-only commits are never discarded by a resume

- **Given** a local branch carrying commits that were never pushed
- **When** the branch is resumed in place
- **Then** the run exits 1 and explains, instead of resetting the branch to the remote
- **Test:** `tests/test_worktree_base.py::test_resume_refuses_to_discard_local_commits`

#### Scenario: a worktree resume never resets a branch either

- **Given** a local branch carrying commits that were never pushed
- **When** the branch is resumed into a worktree
- **Then** the run exits 1, the branch is exactly where it was and no worktree is created
  — the worktree path attaches with `git worktree add` and fast-forwards only, never `-B`
- **Test:** `tests/test_worktree_base.py::test_resume_never_resets_a_local_branch_even_in_a_worktree`
