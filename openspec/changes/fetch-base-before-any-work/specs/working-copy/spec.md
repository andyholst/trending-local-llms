# working-copy

## ADDED Requirements

### Requirement: Every run fetches origin/master before it starts and states the base it read

`AGENTS.md` §6n MUST require a fetch before any work — analysis, review, data read or edit — a
fast-forward pull in a checkout the author owns, and the reporting of the base SHA the work read.

#### Scenario: the rulebook carries the rule

- **Given** AGENTS.md
- **When** the guard reads §6n
- **Then** it carries the always-fetch wording, the `--ff-only` pull, the stated base SHA and the
  machinery for a checkout you own (`make base-check`)
- **Test:** tests/test_worktree_base.py::test_the_rulebook_states_the_rule

#### Scenario: the wording is removed

- **Given** an AGENTS.md without the bullet
- **When** the guard runs
- **Then** it fails, naming the missing half of the rule
- **Test:** tests/test_worktree_base.py::test_the_rulebook_states_the_rule

### Requirement: The §8 guard table names the failure it catches

`AGENTS.md` §8's `tests/test_worktree_base.py` row MUST mention the run that starts from a base it
never fetched or never reported.

#### Scenario: the row

- **Given** AGENTS.md's §8 table
- **When** the guard reads the worktree row
- **Then** the always-fetch failure is named among what the guard catches
- **Test:** tests/test_worktree_base.py::test_the_rulebook_states_the_rule
