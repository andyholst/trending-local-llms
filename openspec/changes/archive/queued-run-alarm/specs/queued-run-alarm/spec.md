# queued-run-alarm

## ADDED Requirements

### Requirement: a job stuck in `queued` past the threshold is reported and turns the run red

The alarm SHALL list the jobs still `queued` in the repo's `queued`/`in_progress` runs and report
the ones queued longer than `--minutes` (default 30), naming the runner label and the age, and the
sweep SHALL exit non-zero when at least one job is stuck.

#### Scenario: a job queued past the threshold is reported

- **GIVEN** a run whose job has been `queued` for 45 minutes,
- **WHEN** the sweep runs with `--minutes 30`,
- **THEN** the job is reported with its label and age, and the sweep exits 1.

- **Test:** `tests/test_queued_run_alarm.py::test_a_long_queued_job_is_reported`

#### Scenario: a short queue is not reported

- **GIVEN** a job queued only 5 minutes,
- **WHEN** the sweep runs with `--minutes 30`,
- **THEN** nothing is reported and the sweep exits 0.

- **Test:** `tests/test_queued_run_alarm.py::test_a_short_queue_is_not_reported`

### Requirement: the comment is posted once per affected run

`--comment` SHALL post exactly ONE comment on each affected run, deduplicated against the alarm's
own marker, so a repeated sweep does not spam.

#### Scenario: a repeat sweep re-comments nothing

- **GIVEN** a run already carrying the alarm's marker comment,
- **WHEN** the sweep runs again with `--comment`,
- **THEN** it posts no second comment.

- **Test:** `tests/test_queued_run_alarm.py::test_comment_is_posted_once_per_run`

### Requirement: the decision lives in the script, reached through a make target

The workflow's `alarm` job SHALL run `make queued-alarm` (never a `scripts/*.py` directly), the
`guard` job SHALL be first and admit the owner, a write+ collaborator and the bot itself with the
`schedule` bypass, and the workflow SHALL carry its own concurrency group.

#### Scenario: the workflow is wired as the rule requires

- **GIVEN** `.github/workflows/queued-alarm.yml`,
- **WHEN** its jobs and its steps are read,
- **THEN** the guard is first, the alarm job calls `make queued-alarm`, and no `run:` invokes a repo script directly.

- **Test:** `tests/test_queued_run_alarm.py::test_the_workflow_guards_first_and_calls_the_make_target`

#### Scenario: the make target passes its variables through

- **GIVEN** `make -n queued-alarm REPO=… MINUTES=… COMMENT=1`,
- **WHEN** the recipe is printed,
- **THEN** it runs `scripts/queued_run_alarm.py` with `--repo`, `--minutes` and `--comment`.

- **Test:** `tests/test_queued_run_alarm.py::test_the_make_target_passes_its_variables_through`

#### Scenario: the one comment uses the default token

- **Given** the alarm workflow, whose single comment is posted through the issues API
- **When** the alarm job's `GH_TOKEN` is read
- **Then** it is the default `github.token` and no secret is interpolated (rule 6e: the owner PAT cannot comment)
- **Test:** `tests/test_queued_run_alarm.py::test_the_workflow_guards_first_and_calls_the_make_target`

#### Scenario: AGENTS.md carries the rule and the guard row

- **Given** AGENTS.md, where this repo's rules live
- **When** its rule list and its section-8 guard table are read
- **Then** rule 6l documents a job stuck in `queued` and names `make queued-alarm`, and the section-8 row names `tests/test_queued_run_alarm.py`
- **Test:** `tests/test_queued_run_alarm.py::test_agents_md_carries_the_rule_and_the_guard_row`
