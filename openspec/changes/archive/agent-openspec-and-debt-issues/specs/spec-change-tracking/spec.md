# spec-change-tracking

## ADDED Requirements

### Requirement: Every change is a tracked OpenSpec change

A change MUST live in `openspec/changes/<name>/` with a `proposal.md`, at least
one `specs/<capability>/spec.md` and a `tasks.md`, created BEFORE the
implementation, and the OpenSpec CLI MUST run in its own container image — never
a host `npm install`, never a second implementation of the same stage.

WHEN an agent starts a change,
THEN it creates the tracked change first (`make openspec-new NAME=<name>`), writes
proposal + capability spec + task checklist, and implements against that checklist.

#### Scenario: the OpenSpec CLI has exactly one code path

- **Given** an agent that needs to create or validate a change
- **When** it runs `make openspec-*`
- **Then** the CLI runs from `openspec/Dockerfile`'s image, pulled by content hash when published and built here when not (`scripts/ensure_image.py ensure-openspec`), with no host npm install anywhere in the repo
- **Test:** `tests/test_ensure_image.py::test_openspec_image_is_hash_tagged_and_pulled_or_built`

#### Scenario: the change directory shape is what the CLI expects

- **Given** the repository
- **When** `openspec validate --changes` runs against `openspec/changes/**`
- **Then** every active change has a proposal, at least one capability spec and a task checklist
- **Test:** CI job `validate` -> `make openspec-check` (`openspec validate --changes`)

### Requirement: A change is not done while a task box is unticked

`tasks.md` MUST be a `- [ ]` checklist whose boxes are ticked the moment the work
is verified; the gate MUST fail while any ACTIVE change still has an unticked box,
and MUST NOT fail for a change that lives under `openspec/changes/archive/`.

WHEN the task gate runs over the active changes,
THEN it fails on an unticked `- [ ]` and ignores checkboxes inside code fences and archived changes.

#### Scenario: an unticked task fails the gate

- **Given** an active change whose `tasks.md` has one worked task and one leftover `- [ ]`
- **When** the task gate runs
- **Then** it exits non-zero and names the change and the line of the unticked box
- **Test:** `tests/test_check_openspec_tasks.py::test_unticked_task_fails_and_names_the_line`

#### Scenario: an archived change is not checked

- **Given** a completed change moved to `openspec/changes/archive/<name>` with its task boxes still unticked
- **When** the task gate runs over all active changes
- **Then** it exits 0 and does not report that change
- **Test:** `tests/test_check_openspec_tasks.py::test_archived_change_is_ignored`

### Requirement: One root index references every change

`OPENSPEC.md` at the repository root MUST list EVERY directory under
`openspec/changes/**` — active and archived — with its issue, PR, capability
specs and `ticked/total` task count, and MUST be generated, not hand-written.

WHEN a change is added, renamed, archived or its issue/PR/tasks change,
THEN the index becomes stale and the check fails until `make openspec-index` regenerates it.

#### Scenario: a change with no index row fails the check

- **Given** a change directory on disk that `OPENSPEC.md` does not list
- **When** the index check runs
- **Then** it exits non-zero and names the change that has no row
- **Test:** `tests/test_openspec_index.py::test_change_with_no_row_fails_the_check`

#### Scenario: the generated index lists every change with its refs and progress

- **Given** an active change with `Issue: #172` and a tasks checklist half ticked
- **When** the index is regenerated
- **Then** its row carries the change name, `active`, `#172`, the capability spec link and `n/m` tasks
- **Test:** `tests/test_openspec_index.py::test_row_carries_issue_specs_and_task_progress`

#### Scenario: the repository's own index is current

- **Given** the committed `OPENSPEC.md`
- **When** `make openspec-index-check` runs on the real repository
- **Then** it exits 0, so CI fails the moment a change lands without the index being regenerated
- **Test:** `tests/test_openspec_index.py::test_real_repo_index_is_current`

### Requirement: The gate runs in CI

`make openspec-check` MUST run validation, the task gate and the index check, and
the PR pipeline MUST call it so a spec-less or stale change cannot merge.

WHEN a PR is opened,
THEN the `validate` job runs `make openspec-check` and a failure turns the PR red.

#### Scenario: qa-validate runs the openspec gate

- **Given** the PR pipeline definition
- **When** the `validate` job's steps are read
- **Then** one of them runs `make openspec-check`, and a test fails if it is removed
- **Test:** `tests/test_workflows.py::test_qa_validate_runs_the_openspec_gate`
