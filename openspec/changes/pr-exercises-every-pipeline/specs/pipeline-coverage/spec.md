# pipeline-coverage

## ADDED Requirements

### Requirement: Every pipeline is PR-exercised or names the test that covers it

Each `.github/workflows/*.yml` MUST either trigger on `pull_request`/`push`, or appear in
`DISPATCH_ONLY_COVERAGE` naming a test module that `make test` executes.

#### Scenario: a dispatch-only workflow with no coverage

- **Given** a workflow that runs only on `workflow_dispatch` and is absent from the map
- **When** `coverage_problems()` is asked
- **Then** it reports the workflow as uncovered
- **Test:** tests/test_workflows.py::test_every_pipeline_is_exercised_on_a_pr_or_names_its_coverage

#### Scenario: a stale coverage entry

- **Given** a workflow that DOES run on a pull request yet is listed as dispatch-only
- **When** `coverage_problems()` is asked
- **Then** the entry is refused, so the map cannot claim coverage it does not have
- **Test:** tests/test_workflows.py::test_every_pipeline_is_exercised_on_a_pr_or_names_its_coverage

#### Scenario: the real tree

- **Given** the repository's workflows and the map
- **When** the guard runs
- **Then** every workflow is classified and every named module exists and is discovered by the runner
- **Test:** tests/test_workflows.py::test_every_pipeline_is_exercised_on_a_pr_or_names_its_coverage
