# secret-output-guard

## ADDED Requirements

### Requirement: The guarded names are derived from the workflows, not remembered

The set of credential NAMES the guard matches MUST be the floor plus every name a
workflow references as a real `${{ secrets.<NAME> }}` expression, so a new provider key
is guarded without editing the guard.

#### Scenario: a workflow adds a new key

- **Given** a tree whose workflow passes `${{ secrets.BRAND_NEW_KEY }}` through `env:` and whose script prints `$BRAND_NEW_KEY`
- **When** the guard scans the tree
- **Then** the print is reported as `prints-secret-value`
- **Test:** tests/test_secret_output.py::test_a_new_workflow_key_is_guarded_without_editing_the_guard

#### Scenario: a floor name with no workflow reference

- **Given** a script that prints `$NOUS_API_KEY` and no workflow mentioning it
- **When** the guard scans the tree
- **Then** it is still reported
- **Test:** tests/test_secret_output.py::test_the_floor_stays_guarded_without_a_workflow_reference

### Requirement: Prose declares nothing

A `secrets.NAME` mentioned in a comment MUST NOT become a guarded name — a comment that
quotes the shape (as `qa-validate.yml` does while explaining the rule) would otherwise
guard a variable that does not exist.

#### Scenario: a workflow comment quotes the expression

- **Given** a workflow whose only mention of `secrets.X` is inside a `#` comment, and a script printing `$X`
- **When** the guard scans the tree
- **Then** no violation is reported
- **Test:** tests/test_secret_output.py::test_a_name_quoted_in_a_comment_declares_nothing
