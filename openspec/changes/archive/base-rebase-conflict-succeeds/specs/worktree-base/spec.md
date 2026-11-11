# worktree-base

## ADDED Requirements

### Requirement: A conflicted rebase succeeds, and says so

`make base-rebase` MUST exit 0 when the rebase conflicts (the work is kept and the push must
proceed) and MUST print `base_rebase=conflict`. Any other failure MUST exit non-zero.

#### Scenario: the rebase conflicts

- **Given** a branch whose rebase conflicts (the script exits 3)
- **When** the caller runs `make base-rebase BRANCH=<branch>`
- **Then** the target exits 0 and prints `base_rebase=conflict`
- **Test:** tests/test_base_rebase_exit_code.py::test_a_conflicted_rebase_succeeds

#### Scenario: a genuine failure is still a failure

- **Given** a rebase that fails for a reason other than a conflict (exit 1, 2 or 4)
- **When** the caller runs `make base-rebase BRANCH=<branch>`
- **Then** the target exits non-zero and does NOT print `base_rebase=conflict`
- **Test:** tests/test_base_rebase_exit_code.py::test_a_real_failure_still_fails
