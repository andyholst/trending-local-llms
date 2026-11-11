# architecture-description

## ADDED Requirements

### Requirement: The guard's boundary is stated where its promise is made

`ARCHITECTURE.md` MUST state what `make architecture-check` proves (presence of every public
target / workflow / script, plus the structural cross-checks below) and what it does **not**
prove (whether a sentence about a real target is true), so a reader is never told more than the
guard can deliver.

#### Scenario: the boundary is documented

- **Given** the repository's `ARCHITECTURE.md`
- **When** the guard's description is read
- **Then** it names both halves — the presence/structure it proves and the prose it cannot read
- **Test:** tests/test_architecture.py::test_doc_states_what_the_guard_does_not_prove

### Requirement: The `validate*` targets' stage lists match the validator's stage map

Every stage named by a `--only` list in the Makefile MUST be a stage `scripts/validate.py`
registers, and every registered stage MUST be selected by at least one `--only` list — compared
against the validator's real map, read by AST, never a copy.

#### Scenario: a list names a stage the validator does not register

- **Given** a Makefile recipe running `validate.py --only data,gone`
- **When** the guard runs
- **Then** it fails, naming the target and the unregistered stage
- **Test:** tests/test_architecture.py::test_validate_only_stage_lists_match_the_validator

#### Scenario: a registered stage is selected by no list

- **Given** a validator whose map carries `schema` and a Makefile with no `--only` list naming it
- **When** the guard runs
- **Then** it fails, naming the stage
- **Test:** tests/test_architecture.py::test_validate_only_stage_lists_match_the_validator

#### Scenario: the corrected list

- **Given** the same validator and a `--only` list naming every registered stage
- **When** the guard runs
- **Then** it reports nothing about stages, so the check is not vacuous
- **Test:** tests/test_architecture.py::test_validate_only_stage_lists_match_the_validator

### Requirement: The pipeline tables' job names match the workflows' real job keys

For every workflow, the job names `ARCHITECTURE.md` §4 claims (its `Job` table rows and its bold
job bullets) MUST be compared with the workflow's actual `jobs:` keys, parsed once by
`scripts/architecture_bot.workflow_jobs`: a described job the workflow does not define fails, a
real job no §4 section names fails, and a workflow with no §4 section of its own fails.

#### Scenario: a described job does not exist

- **Given** a §4 table naming a `sweep` job for a workflow that defines only `guard` and `alarm`
- **When** the guard runs
- **Then** it fails, naming the workflow and the invented job
- **Test:** tests/test_architecture.py::test_pipeline_job_names_match_the_workflow_job_keys

#### Scenario: a real job is not described

- **Given** a workflow defining `guard` and `review` and a §4 table naming only `guard`
- **When** the guard runs
- **Then** it fails, naming the undescribed job
- **Test:** tests/test_architecture.py::test_pipeline_job_names_match_the_workflow_job_keys

#### Scenario: a workflow with no section of its own

- **Given** a workflow the document never gives a §4 subsection
- **When** the guard runs
- **Then** it fails, so the job coverage cannot be vacuous
- **Test:** tests/test_architecture.py::test_pipeline_job_names_match_the_workflow_job_keys

#### Scenario: the fixture is in step

- **Given** the same fixture with the job list corrected
- **When** the guard runs
- **Then** it reports nothing for that workflow
- **Test:** tests/test_architecture.py::test_pipeline_job_names_match_the_workflow_job_keys
