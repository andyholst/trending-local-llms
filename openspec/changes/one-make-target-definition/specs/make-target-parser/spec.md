# one-make-target-definition

## ADDED Requirements

### Requirement: One parser defines what a make target is

A single scan MUST decide what a make target is — a `name:` line at column 0 that is
not a `:=`/`?=`/`+=` assignment nor Makefile scaffolding — and every other count in the
tree MUST be a view of that scan, never a second regex. Both the full set and the
public projection MUST be derived from it.

#### Scenario: every view is a projection of the one scan

- **Given** the repository's `Makefile`
- **When** `make_targets(root)` and `public_targets(root)` are read
- **Then** every public target is a target (`public ⊆ full`) and the public set is
  exactly the full set filtered to lowercase `[a-z][a-z0-9-]*` names
- **Test:** tests/test_architecture.py::test_public_targets_are_a_projection_of_the_full_set

#### Scenario: the checker carries no second parser

- **Given** `scripts/architecture_check.py`
- **When** it is read for its own make-target regular expression
- **Then** it defines none — it imports `public_targets` from `architecture_bot`
- **Test:** tests/test_architecture.py::test_public_targets_are_a_projection_of_the_full_set

#### Scenario: the generated inventory count is unchanged

- **Given** the repository tree
- **When** `make architecture-check` runs
- **Then** the generated `## 10` block still matches the tree (same full-set count)
- **Test:** tests/test_architecture_bot.py::test_real_repository_inventory_is_current
