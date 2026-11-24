# rulebook

## ADDED Requirements

### Requirement: The rulebook names the push-and-verify delivery rule

`AGENTS.md` §7b MUST carry a bullet teaching push-and-verify: a lane makes its change in the worktree,
runs ONLY the fast offline checks, PUSHES, and confirms CI registered on the new head before reporting.
The bullet MUST name the full `make validate`, the whole `make test` and `make live-smoke` as CI-ONLY
on `qa-validate`.

#### Scenario: §7b carries the push-and-verify bullet

- **Given** `AGENTS.md` at the landing head
- **When** the guard reads §7b
- **Then** it carries the lead `Lanes change locally and PUSH; CI verifies`, the fast offline check list,
  the CI-registered confirmation and the phrase `are CI-ONLY`
- **Test:** tests/test_push_and_verify_guard.py::test_rulebook_section_7b_carries_the_push_and_verify_bullet

### Requirement: The §8 guard row names the pin module

`AGENTS.md` §8 MUST carry a row naming `tests/test_push_and_verify_guard.py` beside the three CI-only
gate names, so neither the §7b bullet nor this row can be dropped silently.

#### Scenario: the row is present

- **Given** `AGENTS.md` §8 at the landing head
- **When** the guard scans the table
- **Then** a row names `tests/test_push_and_verify_guard.py` and the backticked `make validate`,
  `make test` and `make live-smoke`
- **Test:** tests/test_push_and_verify_guard.py::test_rulebook_section_8_carries_the_guard_row

#### Scenario: deleting the row turns the guard red

- **Given** the landing head with the §8 row removed
- **When** the guard runs
- **Then** the §8 test fails with `AGENTS.md §8 dropped the push-and-verify guard row` and the module
  exits 1
- **Test:** tests/test_push_and_verify_guard.py::test_rulebook_section_8_carries_the_guard_row
