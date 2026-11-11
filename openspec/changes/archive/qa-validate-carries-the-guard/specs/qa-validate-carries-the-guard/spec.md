# qa-validate-carries-the-guard

## ADDED Requirements

### Requirement: every guarded pipeline has a guard, and qa-validate is one of them

The pipelines listed in `BOT_GUARDS` SHALL each carry the owner / write+
collaborator / `github-actions[bot]` trigger guard as the FIRST step of the job
that carries it, checked BEFORE any secret is read, deciding on BOTH
`github.actor` and `github.triggering_actor`. `qa-validate.yml` SHALL be one of
them: its `guard` job SHALL be its first job and SHALL gate the jobs that read a
secret.

#### Scenario: the real guard script decides every caller class the same way

- **GIVEN** the guard scripts of every pipeline in `BOT_GUARDS`, `qa-validate.yml` included,
- **WHEN** each is run for the owner, a `write`/`maintain`/`admin` collaborator, `github-actions[bot]`, a `read`/`triage` collaborator, a non-collaborator and a stranger re-running an owner run,
- **THEN** the first three SHALL be allowed and the last three refused.

- **Test:** `tests/test_workflows.py::test_guard_behaviour`

#### Scenario: a refused dispatch never reaches the 30-minute job

- **GIVEN** `qa-validate.yml`,
- **WHEN** its jobs are read,
- **THEN** `validate` and `live-smoke` SHALL declare `needs: guard`, and the `guard` job SHALL declare no `needs`.

- **Test:** `tests/test_workflows.py::test_a_guarded_pipeline_gates_the_jobs_that_read_secrets`

### Requirement: a guard admits the repository's own events

A pipeline that declares `pull_request` or `push` SHALL admit those events
without a caller check, because GitHub starts them for the repository itself —
there is no caller to admit — and a PR must be validated whatever its author. A
guard that treated them as a dispatch would refuse every outside contribution
and leave its PR red for ever.

#### Scenario: a stranger's pull request is admitted, a stranger's dispatch is not

- **GIVEN** `qa-validate.yml`'s guard script,
- **WHEN** it is run with `EVENT=pull_request` (or `push`) and a non-collaborator as BOTH actor and triggering actor,
- **THEN** it SHALL exit 0; and with `EVENT=workflow_dispatch` it SHALL exit non-zero.

- **Test:** `tests/test_workflows.py::test_a_repo_event_run_is_admitted_by_its_guard`
