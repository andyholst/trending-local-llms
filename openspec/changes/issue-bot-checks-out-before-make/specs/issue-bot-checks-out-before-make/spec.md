# issue-bot-checks-out-before-make

## ADDED Requirements

### Requirement: a step that calls a repo target runs after the job's checkout

A workflow step whose `run` invokes a `make` target SHALL come after the
`actions/checkout` step of the same job, because the Makefile is part of the
repository and a bare runner has none: the measured failure is
`make: *** No rule to make target 'issue-thread'.  Stop.` in the implementer's
second step, with every later step skipped (#281). A job that calls `make`
without ever checking the repository out SHALL be a finding.

#### Scenario: every make-calling step follows its checkout

- **GIVEN** every `.github/workflows/*.yml`,
- **WHEN** each job's steps are read in order,
- **THEN** every step whose `run` calls `make` SHALL appear after that job's checkout step.

- **Test:** `tests/test_workflows.py::test_a_step_that_calls_make_runs_after_the_checkout`

#### Scenario: the class guard is not vacuous

- **GIVEN** the workflows as they are,
- **WHEN** the make-calling steps are collected,
- **THEN** there SHALL be at least ten of them.

- **Test:** `tests/test_workflows.py::test_a_step_that_calls_make_runs_after_the_checkout`

### Requirement: the implementer's resolver needs no repository

The `implement` job of `issue-bot.yml` SHALL resolve the issue (`open`, branch
name, `implement` output) with `gh` alone, because that step runs before the
checkout; the issue's whole thread SHALL be rendered by its own step after the
checkout, and it SHALL fail loudly when the rendered file is empty.

#### Scenario: the resolver calls no repo target

- **GIVEN** `issue-bot.yml`'s `implement` job,
- **WHEN** the `Resolve the issue` step's script is read,
- **THEN** it SHALL contain no `make` call.

- **Test:** `tests/test_workflows.py::test_a_step_that_calls_make_runs_after_the_checkout`

#### Scenario: the thread is read after the checkout and cannot be empty

- **GIVEN** the `implement` job's steps in order,
- **WHEN** the step that runs `make issue-thread` is located,
- **THEN** it SHALL come after `Checkout master (PAT, so its push re-triggers CI)`
  and SHALL fail on an empty `issue.md`.

- **Test:** `tests/test_workflows.py::test_a_step_that_calls_make_runs_after_the_checkout`
