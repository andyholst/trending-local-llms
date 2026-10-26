# bot-alarm-configuration

## ADDED Requirements

### Requirement: A step declares a setting once

A workflow step MUST NOT declare the same setting in its `env:` **and** assign it a different value
on its command line; `tests/test_workflows.py` MUST fail naming the step, the key and the override.
Passing the env value through (`KEY="$KEY"`) is not an override and stays allowed.

#### Scenario: the measured dead entry

- **Given** a step with `env: MAX_FIXBOT_COMMITS: "2"` and `run: make pr-health … MAX_FIXBOT_COMMITS=2`
- **When** the scan runs
- **Then** it fails naming the step, the key and `MAX_FIXBOT_COMMITS=2`
- **Test:** tests/test_workflows.py::test_a_step_setting_lives_in_env_or_on_the_command_line_never_both

#### Scenario: handing the env value on is not an override

- **Given** a step with `env: REPO: …` and `run: make pr-health REPO="$REPO"`
- **When** the scan runs
- **Then** it reports nothing
- **Test:** tests/test_workflows.py::test_a_step_setting_lives_in_env_or_on_the_command_line_never_both
