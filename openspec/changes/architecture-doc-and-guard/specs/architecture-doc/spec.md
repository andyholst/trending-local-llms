# architecture-doc

## ADDED Requirements

### Requirement: The repository has one description of how it works

`ARCHITECTURE.md` at the repository root MUST describe the data flow and the
contracts, every public `make` target (grouped, with the image it runs in),
every job of every pipeline in `.github/workflows/` with its triggers and gates,
every runner image and how its content-hash tag is decided, every script in
`scripts/`, and the life of a change from issue to merge.

WHEN a reader or an agent needs to know what a target or a pipeline job does,
THEN `ARCHITECTURE.md` answers it without reading the Makefile, four workflow
files and an image Dockerfile.

#### Scenario: the description covers the repository

- **Given** the real repository (55+ public targets, four workflows, three images, ~20 scripts)
- **When** `make architecture-check` runs
- **Then** it exits 0, and the file names the four pipelines and the core targets (`refresh`, `openspec-check`, `data-gap-issue`, …)
- **Test:** `tests/test_architecture.py::test_real_repo_description_is_current`

### Requirement: The description is part of the change

Any change that adds, renames or removes a make target, a stage, a pipeline job
or an image MUST update `ARCHITECTURE.md` in the SAME change, and the
implementer prompt MUST require it, so a bot-maintained change keeps the
description true.

WHEN an implementation adds a target, a job or an image,
THEN the same change updates `ARCHITECTURE.md` and passes `make architecture-check`.

#### Scenario: an undocumented make target fails the check

- **Given** a Makefile with a public target that the description's tables do not name
- **When** the check runs
- **Then** it exits non-zero and names the target and the file to update
- **Test:** `tests/test_architecture.py::test_undocumented_target_is_reported`

#### Scenario: a missing description is caught, not tolerated

- **Given** a tree without `ARCHITECTURE.md`
- **When** the check runs
- **Then** it reports that the file is part of the change (rule 6h)
- **Test:** `tests/test_architecture.py::test_missing_doc_is_a_failure`

#### Scenario: the prompt requires the update

- **Given** the Makefile's implementer prompt
- **When** it is read
- **Then** it requires the `ARCHITECTURE.md` update when a target, a pipeline job, an image or a script changes, and names `make architecture-check` among the checks to run
- **Test:** `tests/test_architecture.py::test_wired_into_ci_the_loop_the_suite_and_the_prompt`

### Requirement: A stale claim is a defect too

The description's §3 target tables MUST NOT name a make target that no longer
exists, and MUST NOT reference a `.github/workflows/*.yml` or `scripts/*` path
that is not in the repository.

WHEN a target is renamed or removed, or a workflow/script is deleted,
THEN the description's own claim about it fails the check until it is corrected.

#### Scenario: a removed target is still described

- **Given** an `ARCHITECTURE.md` whose tables name a target the Makefile no longer has
- **When** the check runs
- **Then** it exits non-zero, naming the stale target
- **Test:** `tests/test_architecture.py::test_stale_target_mention_is_reported`

#### Scenario: a phantom workflow or script reference

- **Given** a description that references `.github/workflows/ghost.yml` and `scripts/ghost.sh`
- **When** the check runs
- **Then** it exits non-zero, naming both references as non-existent
- **Test:** `tests/test_architecture.py::test_phantom_reference_is_reported`

### Requirement: A workflow or script with no description fails

Every file in `.github/workflows/` and every file in `scripts/` MUST be described
in `ARCHITECTURE.md`, so a new pipeline or helper cannot land silently.

WHEN a workflow or a script is added,
THEN the check fails until the description names it.

#### Scenario: an undescribed workflow and script are reported

- **Given** a tree with an extra workflow and an extra script that the description never mentions
- **When** the check runs
- **Then** it exits non-zero, naming each one
- **Test:** `tests/test_architecture.py::test_undocumented_workflow_and_script_are_reported`

### Requirement: The guard runs where a change is judged

`make architecture-check` MUST run in `qa-validate`'s `validate` job, in the fix
loop (before the network-bound checks) and through its test in `make test` — a
guard no pipeline executes is a defect.

WHEN a PR is opened or a fix round runs,
THEN the description is checked, and a failure turns the PR or the round red.

#### Scenario: CI, the loop and the suite all run it

- **Given** the pipeline definition, `scripts/fix_loop.sh` and the Makefile
- **When** their wiring is read
- **Then** the `validate` job runs `make architecture-check`, the fix loop's check list contains it, and `make test` runs `tests/test_architecture.py`
- **Test:** `tests/test_architecture.py::test_wired_into_ci_the_loop_the_suite_and_the_prompt`
