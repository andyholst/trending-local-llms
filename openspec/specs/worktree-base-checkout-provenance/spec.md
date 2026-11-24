# worktree-base-checkout-provenance Specification

## Purpose
TBD - created by archiving change worktree-base-mode-path-1334. Update Purpose after archive.

## Requirements

### Requirement: The branchless modes name the checkout they read

`mode_check`, `mode_advance` (both its fresh and its moved branch) and `mode_adopt` SHALL each print exactly one additive `path=<abs>` line naming the working tree they read, reusing the `path=` key `_summary` and `mode_resume` already emit. No other output line SHALL change and no exit code SHALL change.

#### Scenario: check names the checkout it verified

- **Given** a clean single-ref clone standing at the freshly fetched tip
- **When** `check` runs
- **Then** it exits 0 and stdout carries `path=<that checkout>` beside `fresh=true`
- **Test:** tests/test_worktree_base.py::test_check_advance_and_adopt_name_the_checkout_they_read

#### Scenario: advance names the checkout on both of its branches

- **Given** first a fresh clone, then a remote `master` moved one commit ahead
- **When** `advance` runs twice (the no-op and the fast-forward)
- **Then** BOTH runs carry `path=<that checkout>`, including the branch that resets the tree
- **Test:** tests/test_worktree_base.py::test_check_advance_and_adopt_name_the_checkout_they_read

#### Scenario: adopt names the checkout it writes

- **Given** a dirty clone holding uncommitted implementation work
- **When** `adopt --branch ci/data-gap-2-x` cuts the branch from that HEAD
- **Then** it exits 0 and stdout carries `path=<that checkout>`
- **Test:** tests/test_worktree_base.py::test_check_advance_and_adopt_name_the_checkout_they_read

#### Scenario: a mode that never learned the line is caught

- **Given** the module with the four `print(f"path={cwd}")` lines removed
- **When** the pinning test runs
- **Then** all four of its checks FAIL (a missing line is never confused with the process CWD)
- **Test:** tests/test_worktree_base.py::test_check_advance_and_adopt_name_the_checkout_they_read
