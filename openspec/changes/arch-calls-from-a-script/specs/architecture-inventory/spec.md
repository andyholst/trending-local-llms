# architecture-inventory

## ADDED Requirements

### Requirement: A target reached through a declared script is reported

The inventory MUST report, for a workflow step that runs a script, the targets that script declares
with `# arch-calls: <target> …` — and MUST refuse a declaration naming a target the Makefile does
not define, at both the write and the check path.

#### Scenario: a step runs a declaring script

- **Given** a workflow whose step runs `scripts/fix_loop.sh`, and that script declaring
  `# arch-calls: validate test fix`
- **When** the block is generated
- **Then** the workflow's `calls` line names `make validate`, `make test` and `make fix`
- **Test:** tests/test_architecture_bot.py::test_targets_a_step_reaches_through_a_script_are_reported

#### Scenario: a declaration lies

- **Given** the same script declaring `arch-calls: validate ghost-target`
- **When** the block is generated or checked
- **Then** `_arch_calls_problems` reports `ghost-target` as not a make target, and the ghost never
  appears in the block
- **Test:** tests/test_architecture_bot.py::test_targets_a_step_reaches_through_a_script_are_reported

#### Scenario: the declaration is not the script's role

- **Given** a script whose first comment line is its `arch-calls:` declaration
- **When** the one-line inventory is rendered
- **Then** the declaration is skipped and the script's real description (or `(no docstring)`) is shown
- **Test:** tests/test_architecture_bot.py::test_targets_a_step_reaches_through_a_script_are_reported
