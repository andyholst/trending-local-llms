# architecture-description

## ADDED Requirements

### Requirement: The inventory counts only executed `make` calls

`workflow_targets` MUST report a `make <target>` only where the shell would execute it: a
`make` inside a heredoc body or inside a quoted string MUST NOT be reported, while a real
call whose ARGUMENT is quoted MUST be.

#### Scenario: a heredoc body that mentions a target

- **Given** a `run:` block writing `this PR passes make openspec-check` into a file, then running `make validate`
- **When** the inventory reads the workflow
- **Then** `validate` is reported and `openspec-check` is not
- **Test:** tests/test_architecture_bot.py::test_a_make_written_inside_prose_is_not_a_call

#### Scenario: a quoted sentence

- **Given** `run: echo "the guard runs make openspec-check before anything else"`
- **When** the inventory reads the workflow
- **Then** `openspec-check` is not reported
- **Test:** tests/test_architecture_bot.py::test_a_make_written_inside_prose_is_not_a_call

#### Scenario: a real call with a quoted argument

- **Given** `run: make pr-body ISSUE="$ISSUE"`
- **When** the inventory reads the workflow
- **Then** `pr-body` IS reported (the filter removes strings, not targets)
- **Test:** tests/test_architecture_bot.py::test_a_make_written_inside_prose_is_not_a_call

#### Scenario: the filter does not empty the real inventory

- **Given** the shipped `qa-validate.yml`
- **When** the inventory reads it with the real Makefile's targets
- **Then** `validate`, `validate-search` and `test` are still reported
- **Test:** tests/test_architecture_bot.py::test_a_make_written_inside_prose_is_not_a_call
