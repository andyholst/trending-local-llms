# python-env-utility-batch Specification

## Purpose
TBD - created by archiving change os-agnostic-make-utility-batch-seam. Update Purpose after archive.

## Requirements

### Requirement: The pure utility batch runs through the container seam

Every public target in the Slice 4 utility batch SHALL list `python-env-image` as a prerequisite and run its recipe as a PURE `python3 scripts/…` command behind the ONE `$(PYTHON_RUN)` seam, so a runner with Docker but not the pinned Python/deps produces the same artifact as a provisioned host.

#### Scenario: Each migrated target routes through the seam

- **Given** the Makefile at this change's head
- **When** the Slice 4 seeded set is checked
- **Then** each of `architecture-refresh`, `openspec-record-pr`, `check-agent-skills`, `agent-skills-report`, `cron-install-check`, `vetted-performance`, `secret-output-report` and `scrub-log` carries the `python-env-image` prerequisite and a `$(PYTHON_RUN) python3 scripts/…` recipe
- **Test:** tests/test_workflows.py::test_python_env_seam_routes_migrated_recipes_through_the_container

#### Scenario: The migration is locked by a guard that fails without it

- **Given** the pre-change Makefile with the eight recipes still bare HOST `python3`
- **When** the Slice 4 assertion runs
- **Then** it fails, naming the targets that lost the seam
- **Test:** tests/test_workflows.py::test_python_env_seam_routes_migrated_recipes_through_the_container

#### Scenario: The agent-skills gate pin follows the seam

- **Given** the public `check-agent-skills` target migrated behind `$(PYTHON_RUN)`
- **When** `tests/test_agent_skills.py` reads the Makefile
- **Then** the asserted recipe text includes the seam prefix and the prerequisite
- **Test:** tests/test_agent_skills.py::test_the_gate_is_wired_to_the_lint_target_and_the_suite

### Requirement: Targets that need host state stay host-side

A target whose recipe needs the HOST `.git` common directory or another host-only resource SHALL NOT be routed through `$(PYTHON_RUN)` in this change, and the guard SHALL keep it host-side rather than routing it blindly.

#### Scenario: The self-archive pair waits for its own seam change

- **Given** `self-archive-snapshot` and `self-archive-guard` read the repository's git common dir
- **When** the Slice 4 guard runs
- **Then** neither target carries a `$(PYTHON_RUN)` prefix
- **Test:** tests/test_workflows.py::test_python_env_seam_routes_migrated_recipes_through_the_container
