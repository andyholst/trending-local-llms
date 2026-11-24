## ADDED Requirements

### Requirement: Every workflow declares an explicit, scoped concurrency group

Every workflow under `.github/workflows/` SHALL carry a top-level `concurrency:` block with an explicit non-empty `group` and a boolean `cancel-in-progress`, and the block SHALL be documented by a comment attached directly above it that names its scope and its cancel choice.

#### Scenario: A workflow with no concurrency block is refused

- **Given** a workflow file without a top-level `concurrency:` block
- **When** the workflow wiring suite scans the tree
- **Then** the check names the file and fails
- **Test:** tests/test_workflows.py::test_every_workflow_declares_an_explicit_scoped_concurrency_group

#### Scenario: An undocumented group is refused

- **Given** a workflow whose `concurrency:` block has no attached comment naming group/key/scope and cancel-in-progress
- **When** the suite reads the comment block directly above the key
- **Then** the check names the file and fails
- **Test:** tests/test_workflows.py::test_every_workflow_declares_an_explicit_scoped_concurrency_group

### Requirement: A PR pipeline cancels only its own superseded run

`qa-validate.yml` and `pr-closure.yml` SHALL key their group by the workflow, the event name and the pull request number, fall back to `github.ref` for events that carry no PR number, and set `cancel-in-progress: true`.

#### Scenario: Two consecutive pushes to one PR

- **Given** a `pull_request` run of `qa-validate` in flight for PR 1560
- **When** a newer push to the same PR starts a second run
- **Then** both runs resolve to the same group and the first is cancelled, while PR 1561 resolves to a different group
- **Test:** tests/test_workflows.py::test_every_workflow_declares_an_explicit_scoped_concurrency_group

#### Scenario: Another purpose or pipeline is never cancelled

- **Given** the resolved groups for a PR, a push to master, a dispatch and the sibling PR pipeline
- **When** the checked-in group expressions are evaluated offline
- **Then** all four groups differ
- **Test:** tests/test_workflows.py::test_every_workflow_declares_an_explicit_scoped_concurrency_group

### Requirement: Serialised pipelines queue instead of dropping a run

Every workflow that is not a PR pipeline SHALL keep `cancel-in-progress: false` and a group scoped to its own purpose: its own name, or `issue-bot`'s per-issue key.

#### Scenario: The ten non-PR pipelines keep their serialising semantics

- **Given** every workflow except `qa-validate.yml` and `pr-closure.yml`
- **When** the suite reads each `concurrency:` block
- **Then** `cancel-in-progress` is false and the group equals the workflow's own name (issue-bot: the per-issue key with its sweep fallback)
- **Test:** tests/test_workflows.py::test_every_workflow_declares_an_explicit_scoped_concurrency_group

#### Scenario: No two purposes share a static group

- **Given** every static group string declared in the tree
- **When** the suite collects them
- **Then** each appears for exactly one workflow
- **Test:** tests/test_workflows.py::test_every_workflow_declares_an_explicit_scoped_concurrency_group
