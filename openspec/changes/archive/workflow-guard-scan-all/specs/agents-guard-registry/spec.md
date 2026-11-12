## ADDED Requirements

### Requirement: The tree-wide guard scan is a pipeline stage

The repository SHALL run `make check-workflow-guards` (`scripts/check_workflow_guards.py`) as part of `make lint`, so every PR, every fix-loop round and every human run executes a scan of EVERY file in `.github/workflows/` — derived from the tree, never from a hand-kept list — and the scan fails (exit 1) naming each offender, or fails (exit 2) when the tree itself cannot be read.

#### Scenario: every workflow is scanned and carries its guard
- **Given** the repository's real `.github/workflows/` directory
- **When** `scan_tree` runs over it
- **Then** every `.yml` appears in the report, every workflow's guard job is found by scanning, and no problem is reported
- **Test:** tests/test_workflow_guards.py::test_the_real_tree_scans_green_and_covers_every_workflow

#### Scenario: the real guard scripts decide every caller class
- **Given** every dispatchable workflow's guard `run:` script, executed with a stub `gh` standing in only for the collaborator-permission API
- **When** each of the nine caller classes (owner, write/maintain/admin collaborator, the bot, read-only, triage, non-collaborator, stranger re-running an owner's run) is run against it
- **Then** the allowed classes exit 0 and the refused classes exit 1, for every workflow in the tree
- **Test:** tests/test_workflow_guards.py::test_the_real_guard_scripts_decide_every_caller_class

### Requirement: No pipeline may wait on a human to start

No job in any workflow may declare `environment:` (a required-approval gate is a human gate), every scheduled pipeline's guard must carry the schedule bypass and must pass a scheduled run with no caller identity, and every repository event a workflow declares (`pull_request`, `push`, `issues`) must be admitted by its guard whatever the actor — GitHub starts those for the repository itself.

#### Scenario: an approval-gated start turns the scan red
- **Given** a fixture tree where a health pipeline's job carries `environment: Production`
- **When** the scan runs over it
- **Then** the scan reports the `environment:` gate for that workflow and exits 1, while the ungated copy of the same workflow stays clean
- **Test:** tests/test_workflow_guards.py::test_a_second_pipeline_with_an_environment_gate_fails_the_scan

#### Scenario: a cron starts mechanically with no caller identity
- **Given** a real cron pipeline's guard script
- **When** it is executed with event `schedule` and empty actor and triggering actor
- **Then** it exits 0 — the scheduled start never depends on a person
- **Test:** tests/test_workflow_guards.py::test_a_scheduled_pipeline_starts_from_no_human

#### Scenario: a repository event is admitted whatever its actor
- **Given** qa-validate's, pr-closure's and issue-bot's real guard scripts
- **When** each runs for its declared repository events with a stranger as actor and triggering actor
- **Then** each exits 0 — a PR is validated whatever its author
- **Test:** tests/test_workflow_guards.py::test_repository_events_are_admitted_whatever_the_actor

### Requirement: Every escape shape the scan claims to catch is proven red

The scan SHALL be verified against planted fixture workflows — one defect each in an otherwise-correct pipeline — so that a guardless workflow, a guard that needs a job, a guard touching a secret, a cron without the bypass, a refused repository event, a guard that would admit a stranger, a job that skips the guard, and a trigger outside the decided decision surface each turn the stage red with the named problem.

#### Scenario: planted fixtures go red, each for its own defect
- **Given** a fixture tree carrying the nine planted workflows built from the real guard script
- **When** the scan runs over it
- **Then** every fixture is reported by at least one problem naming its defect, and `main` exits 1
- **Test:** tests/test_workflow_guards.py::test_planted_fixtures_go_red_for_each_escape

#### Scenario: an unreadable tree is loud, never clean
- **Given** a path with no `.github/workflows/` directory
- **When** `main` runs against it
- **Then** it exits 2 and names the missing directory
- **Test:** tests/test_workflow_guards.py::test_main_exits_2_when_the_tree_cannot_be_read

### Requirement: The guard decision has ONE implementation

The CI stage and the workflow suite SHALL share one caller table and one guard-execution harness: `tests/test_workflows.py` imports `GUARD_CALLERS`, `GUARD_PERMS`, `REPO_EVENTS`, `guard_ok` and `run_guard_script` from `scripts/check_workflow_guards.py` instead of keeping copies.

#### Scenario: the scan target is wired through the Makefile into lint
- **Given** the Makefile, `qa-validate.yml` and `scripts/fix_loop.sh`
- **When** the wiring is checked
- **Then** `check-workflow-guards` is defined, bundled in the `lint:` recipe, and `make lint` is run by both the pipeline and the fix loop
- **Test:** tests/test_workflow_guards.py::test_the_scan_is_wired_through_the_makefile_into_lint
