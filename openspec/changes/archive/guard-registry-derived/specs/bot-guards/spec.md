# bot-guards

## ADDED Requirements

### Requirement: the guarded pipelines are derived from the tree

The set of guarded pipelines SHALL be derived from the workflows themselves —
every workflow whose jobs contain a trigger guard step (a step whose name carries
`guard`) — and the hand-maintained registry SHALL be checked against that
derivation in BOTH directions. A workflow that carries a guard but is missing
from the registry SHALL fail, and a registered pipeline that no longer carries a
guard step SHALL fail. They SHALL also agree on WHICH job holds the guard.

#### Scenario: a guard nobody registered fails the suite

- **GIVEN** a workflow in the tree carrying a trigger guard step, absent from `BOT_GUARDS`,
- **WHEN** the suite runs,
- **THEN** it SHALL fail naming the unregistered workflow.

- **Test:** `tests/test_workflows.py::test_the_guard_registry_is_derived_from_the_tree`

#### Scenario: a registered pipeline that lost its guard fails the suite

- **GIVEN** an entry in `BOT_GUARDS` whose workflow no longer carries a guard step,
- **WHEN** the suite runs,
- **THEN** it SHALL fail naming the vanished guard.

- **Test:** `tests/test_workflows.py::test_the_guard_registry_is_derived_from_the_tree`

#### Scenario: the registry names the job the guard is actually in

- **GIVEN** a registry entry naming a job other than the one holding the guard,
- **WHEN** the suite runs,
- **THEN** it SHALL fail with both names.

- **Test:** `tests/test_workflows.py::test_the_guard_registry_is_derived_from_the_tree`

#### Scenario: the derivation is not vacuous

- **GIVEN** the workflows as they are,
- **WHEN** the guarded pipelines are derived,
- **THEN** the result SHALL be non-empty (a scan that finds nothing proves nothing).

- **Test:** `tests/test_workflows.py::test_the_guard_registry_is_derived_from_the_tree`

### Requirement: every dispatchable workflow carries a guard

A workflow that declares `workflow_dispatch` SHALL carry a trigger guard, because
a manual start is the one start a caller chooses — the guard is what admits only
the owner, a `write`/`maintain`/`admin` collaborator, or `github-actions[bot]`.

#### Scenario: a dispatchable pipeline with no guard fails the suite

- **GIVEN** a workflow declaring `workflow_dispatch` whose jobs contain no guard step,
- **WHEN** the suite runs,
- **THEN** it SHALL fail naming that workflow.

- **Test:** `tests/test_workflows.py::test_the_guard_registry_is_derived_from_the_tree`
