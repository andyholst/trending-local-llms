# rulebook

## ADDED Requirements

### Requirement: The rulebook states the authorship rule, not just that a guard exists

`AGENTS.md` §2 MUST carry a rule naming the two allowed identities, the automation identities that
must not be refused, the fact that the guard reads the identity AND the message, and the loud
failure on an unreadable range.

#### Scenario: a reader asks who may commit

- **Given** `AGENTS.md` §2
- **When** a reader looks for the authorship rule
- **Then** rule `3f` names `Andy Holst`, `Asimov Agent`, `github-actions[bot]`, `GitHub <noreply@github.com>`, and `make check-commit-authorship`
- **Test:** tests/test_rule_numbers.py::main

### Requirement: The owed guard rows exist beside the guards they describe

Every guard that an owed-row issue named MUST have its §8 row, and the rows MUST carry the
measured failure rather than a generic phrase.

#### Scenario: the four owed rows

- **Given** `AGENTS.md` §8
- **When** the rows are read
- **Then** `engine_min_version`, the search legs' engine rule, the fix loop's time bound, and the derived guard registry each have a row, and the `tests/test_workflows.py` row names the agent identity instead of "no git identity"
- **Test:** tests/test_architecture.py::main
