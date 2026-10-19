# agent-alias

## ADDED Requirements

### Requirement: Every agent call passes the alias from its one definition

Every `hermes -z` continuation line MUST pass `-m $(HERMES_ALIAS)` — the variable the
image build uses to write the alias into the config — and no recipe may carry the alias
name as a literal.

#### Scenario: the makefile is read

- **Given** the repository's `Makefile`
- **When** the alias guard reads its `\t\t-m …` recipe lines
- **Then** every one of them uses `$(HERMES_ALIAS)`, and no non-comment line carries `-m <the alias value>`
- **Test:** tests/test_hermes_prompts.py::test_the_alias_has_exactly_one_definition

#### Scenario: a dry run expands to the defined alias

- **Given** the same Makefile, with `HERMES_ALIAS` defined
- **When** `make -n <hermes target>` runs for every hermes target
- **Then** each printed command carries `-m <the defined alias> --reasoning`
- **Test:** tests/test_hermes_prompts.py::test_the_alias_has_exactly_one_definition

### Requirement: The alias guards cannot pass by finding nothing

The checks that scan the Makefile for hermes call lines MUST count the variable form, so
a recipe set that stopped using it fails instead of matching zero lines.

#### Scenario: the recipe scan finds every call

- **Given** the repository's `Makefile`
- **When** the reasoning-flag and non-interactive guards scan for model-flag lines
- **Then** they find the full set (8 or more) and each carries its flags
- **Test:** tests/test_hermes_prompts.py::test_makefile_prompts_cap_reasoning
