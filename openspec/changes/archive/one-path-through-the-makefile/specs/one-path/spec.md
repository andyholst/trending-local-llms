# one-path

## ADDED Requirements

### Requirement: no test replaces the system under test

A test file SHALL NOT patch, rebind or fake a symbol the product defines under `scripts/`; an
external system MAY stand in.

#### Scenario: patching a product symbol is refused

- **GIVEN** a test that patches a `scripts.<module>.<symbol>` path or rebinds a symbol imported
  from `scripts/` to a `MagicMock`,
- **WHEN** the guard reads the suite,
- **THEN** it reports that file as replacing the system under test.

- **Test:** `tests/test_makefile_only.py::test_a_test_does_not_replace_the_system_under_test`

#### Scenario: the current suite is clean

- **GIVEN** this repository's tests,
- **WHEN** the guard runs over them,
- **THEN** no test patches a product symbol, and the network-level stand-ins are not flagged.

- **Test:** `tests/test_makefile_only.py::test_a_test_does_not_replace_the_system_under_test`

### Requirement: every workflow step goes through the Makefile

A workflow `run:` SHALL reach the product only through a `make` target, never by invoking a repo
script or a test runner directly.

#### Scenario: a direct script invocation is refused

- **GIVEN** a workflow whose `run:` contains `python3 scripts/…`, `bash scripts/…` or a bare
  `pytest`,
- **WHEN** the guard reads the workflows,
- **THEN** it reports that workflow and line.

- **Test:** `tests/test_makefile_only.py::test_every_workflow_step_goes_through_make`

### Requirement: a target a workflow calls exists, and the gate is called

Every `make <target>` a workflow invokes SHALL be defined in the Makefile, and each CI gate target
SHALL be called by at least one workflow.

#### Scenario: a renamed target is caught

- **GIVEN** a workflow calling a target the Makefile no longer defines,
- **WHEN** the guard cross-checks the two,
- **THEN** the missing target is reported, and every gate target is confirmed called.

- **Test:** `tests/test_makefile_only.py::test_workflows_only_call_targets_that_exist`

### Requirement: the PR pipeline runs the gate through make

`qa-validate.yml` SHALL run on `pull_request` and on push, and SHALL run the gate via `make test`.

#### Scenario: the PR pipeline is the gate

- **GIVEN** `qa-validate.yml`,
- **WHEN** its triggers and commands are read,
- **THEN** it has the `pull_request` and `push` triggers and calls `make test`.

- **Test:** `tests/test_makefile_only.py::test_every_target_the_ci_gate_calls_is_reachable_from_the_makefile`
