# architecture-description

## ADDED Requirements

### Requirement: Every script has a role in §6

`ARCHITECTURE.md` §6 ("The scripts") MUST carry one table row per file in `scripts/`,
whose first cell is the script's path. `make architecture-check` MUST fail when a script
has no such row, naming the file, even when the generated §10 block names it — a name in
the block is not a role a reader can use.

#### Scenario: a script named only in the generated block is reported

- **Given** a tree with `scripts/thing.py` whose document mentions it (§4) but has no §6 row
- **When** `scripts/architecture_check.py` runs
- **Then** it reports `scripts/thing.py` as having no row in §6, and the finding disappears once the row is added
- **Test:** `tests/test_architecture.py::test_a_script_named_only_in_the_generated_block_has_no_role`

#### Scenario: the real repository satisfies it

- **Given** this repository after the change
- **When** `make architecture-check` runs
- **Then** it exits 0, and §6 has a row for every one of the scripts on disk
- **Test:** `tests/test_architecture.py::test_real_repo_description_is_current`

### Requirement: The missing roles are written from the code, not guessed

The 9 scripts that had no §6 row MUST gain a row describing what the script actually does
(its real modes, exits and wiring), citing the issue that introduced the behaviour.

#### Scenario: the nine measured gaps are closed

- **Given** `architecture_bot.py`, `code_review.py`, `env_int.py`, `install_hermes_ci.sh`, `pr_health.py`, `queued_run_alarm.py`, `refresh_base.py`, `sweep_alarm.py`, `verify_closure.py`
- **When** the document is checked
- **Then** each has a row in §6 and no finding names it
- **Test:** `tests/test_architecture.py::test_real_repo_description_is_current`
