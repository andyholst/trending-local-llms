# pipeline-repair

## ADDED Requirements

### Requirement: The fix-bot repair pipeline is retired and stays retired

No workflow file named `fix-bot.yml` may exist under `.github/workflows/`; no workflow
may name it, dispatch it, or carry a job named `dispatch-fixbot`; no Makefile recipe may
reach it; and exactly ONE pipeline (`issue-bot.yml`) runs the agent fix loop
`scripts/fix_loop.sh`.

#### Scenario: the pipeline file is gone

- **Given** the repository tree
- **When** the retirement guard lists `.github/workflows/*.yml`
- **Then** no `fix-bot.yml` exists, and no workflow text names `fix-bot.yml` or
  `dispatch-fixbot`
- **Test:** tests/test_workflows.py::test_fix_pipeline_retired

#### Scenario: only the implementer runs the fix loop

- **Given** every workflow's job steps
- **When** the guard collects the workflows whose steps run `scripts/fix_loop.sh`
- **Then** the list is exactly `["issue-bot.yml"]`
- **Test:** tests/test_workflows.py::test_fix_pipeline_retired

#### Scenario: no make recipe reaches the retired pipeline

- **Given** the Makefile
- **When** non-comment lines are scanned for `fix-bot`
- **Then** none carries it
- **Test:** tests/test_workflows.py::test_fix_pipeline_retired

### Requirement: A red validate dispatches no repairer

`qa-validate.yml` performs no pipeline dispatch from any job step (no `gh workflow run`,
no `actions/workflows/.../dispatches` call); a red `validate` stays red with its
`qa-report` artifact as the handoff. Its own `on: workflow_dispatch:` trigger — a human
re-running validation — is not a dispatch to any pipeline.

#### Scenario: qa-validate dispatches nothing

- **Given** `qa-validate.yml`'s job steps
- **When** the guard scans them for dispatch calls
- **Then** none is found, and the workflow names no `dispatch-fixbot` job
- **Test:** tests/test_workflows.py::test_qa_validate

#### Scenario: a red fix loop reds the run, not a dispatch

- **Given** the implementer's fix loop returning red
- **When** the workflow wiring is read
- **Then** the loop's job is the last repair authority and qa-validate dispatches
  nothing to any repair pipeline
- **Test:** tests/test_workflows.py::test_a_red_fix_loop_reds_the_run

### Requirement: The silent-PR sweep reports only

`make pr-health` flags every silent PR and comments the remedy; it dispatches no
repairer, carries no `MAX_FIXBOT_COMMITS` variable, and `scripts/pr_health.py` contains
no dispatch path.

#### Scenario: the sweep dispatches nothing

- **Given** `pr-health.yml`'s jobs and `scripts/pr_health.py`
- **When** the guard reads both
- **Then** no `workflow_dispatch` call exists in either, and findings() still
  classifies every silent PR
- **Test:** tests/test_pr_health.py::test_a_silent_pr_is_reported_and_nothing_is_dispatched

#### Scenario: the real target runs report-only

- **Given** the real Makefile and script with a stub `gh` standing in for the network
- **When** `make pr-health REPO=x/y COMMENT=1` runs
- **Then** it exits 0, prints `[pr-health]`, and the Makefile names no
  `MAX_FIXBOT_COMMITS` for it
- **Test:** tests/test_pr_health.py::test_the_real_target_runs_report_only
