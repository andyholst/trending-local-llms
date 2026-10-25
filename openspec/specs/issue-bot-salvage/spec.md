# issue-bot-salvage Specification

## Purpose
TBD - created by archiving change issue-bot-salvage. Update Purpose after archive.

## Requirements

### Requirement: A detached run that left work behind is salvaged, not discarded

After the implement leg, the issue-bot MUST read the checkout and report whether it is dirty
(`git status --porcelain`, which ignores the gitignored scratch files). The commit/push step MUST run
when the leg exited 0 **or** the tree is dirty, and the "Fail loudly" step MUST NOT fail a run whose
tree was salvaged. A detached run whose tree is clean stays red, because there is nothing to review.

#### Scenario: a dirty tree with a non-zero exit is salvaged

- **Given** a run whose `make implement-issue` exited 3 (the agent asked for input) and whose
  checkout carries changes
- **When** the salvage step runs
- **Then** it reports `dirty=true`, the commit/push step runs, and the run is not failed as
  "produced no implementation"
- **Test:** `tests/test_workflows.py::test_issue_bot_salvages_a_detached_runs_work`

#### Scenario: a clean tree with a non-zero exit stays red

- **Given** the same exit code and an unchanged checkout
- **When** the salvage step runs
- **Then** it reports `dirty=false` and the "Fail loudly" step fails the run, naming rc=3 as the agent
  asking for input
- **Test:** `tests/test_workflows.py::test_issue_bot_salvages_a_detached_runs_work`

#### Scenario: the shipped step really reads a git checkout

- **Given** a temporary git repository, clean and then with one changed file
- **When** the step's own `run:` text is executed in it with `GITHUB_OUTPUT` set
- **Then** it writes `dirty=false` for the clean tree and `dirty=true` for the changed one
- **Test:** `tests/test_workflows.py::test_issue_bot_salvages_a_detached_runs_work`
