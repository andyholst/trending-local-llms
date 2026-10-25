# issue-bot-artifacts

## ADDED Requirements

### Requirement: A recipe a workflow redirects into a content file is silent

Every `make <target> … > <file>` a workflow performs, where the destination is not a
`*.log` capture, MUST resolve to a recipe whose command lines all start with `@`, so the
file holds only the target's own output. `make`'s echoed recipe line MUST NOT reach a file
another step reads as content.

#### Scenario: the implementer's specification file

- **Given** `issue-bot.yml`'s `make issue-thread … > issue.md`
- **When** the guard reads the Makefile
- **Then** `issue-thread`'s command lines are all silenced, and `issue.md` starts with the
  issue, not with `python3 scripts/issue_thread.py …`
- **Test:** tests/test_workflows.py::test_a_recipe_redirected_into_a_file_never_echoes_its_own_command

#### Scenario: the guard is not vacuous

- **Given** the shipped workflows
- **When** the guard collects redirects
- **Then** it finds at least one content redirect and `issue-thread` is among them
- **Test:** tests/test_workflows.py::test_a_recipe_redirected_into_a_file_never_echoes_its_own_command

#### Scenario: a log capture is exempt

- **Given** `make implement-issue > implement.log 2>&1`
- **When** the guard classifies redirects
- **Then** the `*.log` destination is not treated as content, so its recipe may echo
- **Test:** tests/test_workflows.py::test_a_recipe_redirected_into_a_file_never_echoes_its_own_command
