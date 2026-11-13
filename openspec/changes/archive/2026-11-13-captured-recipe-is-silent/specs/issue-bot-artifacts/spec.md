# issue-bot-artifacts

## ADDED Requirements

### Requirement: A recipe whose stdout a workflow captures is silent

Every `$(make <target>)` (or `` `make <target>` ``) a workflow performs MUST resolve to a
recipe whose command lines all start with `@`, so the captured value begins with the
product's own output rather than make's echoed command.

#### Scenario: the sweep's pick

- **Given** `OUT=$(make issue-pick)` in `issue-bot.yml`
- **When** the guard reads the Makefile
- **Then** `issue-pick`'s command lines are all silenced, and `OUT` is exactly `issue=<n>`
- **Test:** tests/test_workflows.py::test_a_captured_recipe_is_silent

#### Scenario: the guard is not vacuous

- **Given** the shipped workflows
- **When** the guard collects captures
- **Then** it finds at least one and `issue-pick` is among them
- **Test:** tests/test_workflows.py::test_a_captured_recipe_is_silent

#### Scenario: a human-facing target may still echo

- **Given** `make issue-queue`, whose output a person reads
- **When** the guard classifies targets
- **Then** it is not required to be silenced (it is not captured by any workflow)
- **Test:** tests/test_workflows.py::test_a_captured_recipe_is_silent
