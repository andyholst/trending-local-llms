# model-pin

## ADDED Requirements

### Requirement: The agent model pin is a dated snapshot

`HERMES_MODEL` MUST name the dated snapshot of the model the pipeline runs, never
the undated family alias, so the model behind a published image cannot change
without a commit.

#### Scenario: the pin is the dated snapshot

- **Given** the Makefile's `HERMES_MODEL` and the undated family alias the endpoint also serves
- **When** the pin guard scans the pipeline files
- **Then** the pin is the dated id, the retired SKU appears nowhere, and the check passes
- **Test:** tests/test_search_budget.py::test_no_stale_model_pin

#### Scenario: a bump back to the floating alias

- **Given** a `HERMES_MODEL` set to `deepseek/deepseek-v4.1-flash` (no date suffix)
- **When** the pin guard runs
- **Then** it fails, naming the value it read, instead of passing silently
- **Test:** tests/test_search_budget.py::test_no_stale_model_pin

### Requirement: The alias the bots call is checked against the same pin

`_hermes-alias-check` MUST compare the written alias to `HERMES_MODEL`, so a
stub agent answering a different model is refused and the image cannot ship an
alias for a model the pipeline does not run.

#### Scenario: the alias check on the pinned model

- **Given** a stub `hermes` answering the pinned model, provider `custom`, `key_env=NOUS_API_KEY`
- **When** `make _hermes-alias-check` runs
- **Then** it exits 0 and prints what it proved
- **Test:** tests/test_install_hermes_ci.py::test_the_alias_check_passes_on_the_pin_and_fails_on_a_different_one
