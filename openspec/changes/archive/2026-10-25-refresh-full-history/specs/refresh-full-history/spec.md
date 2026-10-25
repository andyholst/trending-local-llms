# refresh-full-history

## ADDED Requirements

### Requirement: A job that runs the suite checks out the whole history

Every workflow job that runs `make test`, `make qa-report` or `make check-commit-authorship` MUST
check out with `fetch-depth: 0`. `actions/checkout` defaults to a depth-1 clone and the authorship
guard reads `git log`, so a shallow checkout makes that job's suite red by construction — and a
permanently red advisory QA pass hides every real failure behind it.

#### Scenario: the shipped pipelines that run the suite are full-history

- **Given** every workflow under `.github/workflows/`
- **When** the guard collects the jobs whose `run:` blocks call `make test`, `make qa-report` or
  `make check-commit-authorship`
- **Then** each of those jobs has an `actions/checkout` step with `fetch-depth: 0`
- **And** the guard found at least two such jobs, so it is not vacuous
- **Test:** `tests/test_workflows.py::test_a_job_that_runs_the_suite_checks_out_the_whole_history`

#### Scenario: the refresh aggregate is the QA runner the guard is about

- **Given** `refresh-bot.yml`'s `aggregate` job
- **When** its steps are read
- **Then** it runs `make qa-report`, and its checkout asks for the full history
- **Test:** `tests/test_workflows.py::test_a_job_that_runs_the_suite_checks_out_the_whole_history`

#### Scenario: a comment that names the check is not a call

- **Given** a job whose `run:` block mentions `make check-commit-authorship` only inside a shell
  comment (`architecture-bot.yml`'s commit step)
- **When** the guard reads it
- **Then** the job is not counted as a suite runner and is not required to fetch the full history
- **Test:** `tests/test_workflows.py::test_a_job_that_runs_the_suite_checks_out_the_whole_history`
