# rulebook

## ADDED Requirements

### Requirement: §6b pipeline claims are the bullet lines, never prose tokens

`make architecture-check`'s rulebook reader SHALL treat only the section's pipeline bullets
— a line starting ``- **`<name>.yml`** ``, the shape §6b requires — as claims that a pipeline
exists. A backticked token ending in `.yml` inside a prose sentence SHALL NOT be read as a
claim, so the section can describe its own failure mode without turning the guard red.

#### Scenario: prose naming a backticked `.yml` does not register as a claim

- **Given** a fixture tree whose §6b carries, after its real bullets, a prose sentence
  naming a backticked `sneaky.yml` that the workflows dir does not hold
- **When** `make architecture-check` reads the rulebook's pipeline claims
- **Then** no problem names `sneaky.yml` and the tree stays green in that direction
- **Test:** tests/test_architecture.py::test_prose_naming_a_backticked_yml_is_not_a_claim

#### Scenario: a bullet naming a pipeline the tree lacks is still reported

- **Given** a fixture §6b bullet ``- **`ghost.yml`**`` with no such workflow in the tree
- **When** the checker compares the rulebook's claims against `.github/workflows/`
- **Then** the phantom bullet is named (`AGENTS.md §6b names \`ghost.yml\`` … `not a workflow`)
  and the real `ci.yml` is not blamed
- **Test:** tests/test_architecture.py::test_a_rulebook_line_with_no_workflow_is_reported
