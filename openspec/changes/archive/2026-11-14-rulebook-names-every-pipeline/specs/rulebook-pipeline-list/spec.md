# rulebook-pipeline-list

## ADDED Requirements

### Requirement: The rulebook names every pipeline in the tree

`AGENTS.md` §6b MUST name every workflow file in `.github/workflows/`. `make
architecture-check` MUST fail when a workflow in the tree is not named there, naming
the file, and MUST fail when §6b names a `.yml` that is not a workflow in the tree. A
missing `AGENTS.md` MUST be a finding rather than a skip, so deleting the file cannot
silence the guard.

#### Scenario: an unlisted pipeline is reported and naming it turns the check green

- **Given** a tree whose `AGENTS.md` §6b names only `ci.yml` while `.github/workflows/` holds `ci.yml` and `extra.yml`
- **When** `scripts/architecture_check.py` runs
- **Then** it reports `extra.yml` as not named in `AGENTS.md` §6b, and the finding disappears once a §6b line names it
- **Test:** `tests/test_architecture.py::test_a_pipeline_missing_from_the_rulebook_is_reported`

#### Scenario: a §6b line for a workflow that does not exist is reported

- **Given** a tree whose `AGENTS.md` §6b names `ghost.yml` and whose `.github/workflows/` does not hold it
- **When** `scripts/architecture_check.py` runs
- **Then** it reports that `AGENTS.md` §6b names `ghost.yml`, which is not a workflow in the tree
- **Test:** `tests/test_architecture.py::test_a_rulebook_line_with_no_workflow_is_reported`

#### Scenario: the real repository names every pipeline

- **Given** this repository after the change
- **When** `make architecture-check` runs
- **Then** it exits 0, and `AGENTS.md` §6b names every one of the workflows on disk
- **Test:** `tests/test_architecture.py::test_real_repo_description_is_current`

### Requirement: The rulebook's pipeline list says where each pipeline's shape lives

`AGENTS.md` §6b MUST state that `ARCHITECTURE.md` §4 is the canonical enumeration of
each pipeline's triggers, jobs and `make` targets, while §6b is the rulebook entry
that names the pipeline and the rule it enforces — so the split rule 6h draws between
the rulebook and the description is visible where the list is read.

#### Scenario: a reader of §6b is told where the shape is described

- **Given** `AGENTS.md` §6b
- **When** the section is read
- **Then** it names `ARCHITECTURE.md` §4 as canonical for a pipeline's shape, and every pipeline listed there carries the rule it enforces
- **Test:** `tests/test_architecture.py::test_the_rulebook_points_at_the_canonical_pipeline_description`

### Requirement: A new workflow must be listed in the same change

`AGENTS.md` rule 6h MUST state that a workflow added to `.github/workflows/` is named
in §6b in the same change, alongside the existing requirement to describe it in
`ARCHITECTURE.md`.

#### Scenario: rule 6h names the §6b obligation

- **Given** `AGENTS.md` §2 rule `6h`
- **When** a contributor adds a pipeline
- **Then** the rule tells them §6b must name it and that `make architecture-check` fails otherwise
- **Test:** `tests/test_architecture.py::test_rule_6h_names_the_rulebook_obligation`
