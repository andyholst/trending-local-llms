# pr-ci

## ADDED Requirements

### Requirement: A merged PR's claimed closures are verified

After a merge, the pipeline MUST read the merged PR's `closingIssuesReferences` and fail when one
is not closed, naming the issue and its state.

#### Scenario: the measured PR #272 shape

- **Given** a merged PR referencing #271 (closed) and #276 (open)
- **When** `verify-closure` runs
- **Then** it exits 1 and names #276, its state and rule 6e
- **Test:** tests/test_verify_closure.py::test_a_merge_that_left_the_issue_open_fails_loudly

#### Scenario: a clean merge

- **Given** a merged PR whose reference is closed
- **When** `verify-closure` runs
- **Then** it exits 0 and says how many issues it closed
- **Test:** tests/test_verify_closure.py::test_a_merge_that_closed_its_issue_passes

### Requirement: An unreadable state is loud, never a pass

A `gh` failure MUST exit non-zero and quote the tool's own message.

#### Scenario: gh errors

- **Given** a `gh` that exits 1
- **When** `verify-closure` runs
- **Then** it exits non-zero and quotes `exited 1`
- **Test:** tests/test_verify_closure.py::test_an_unreadable_state_is_loud_never_a_pass

### Requirement: The check is wired to a target and to the merge job

`make verify-closure` MUST run the script, and `auto-merge` MUST call it after merging.

#### Scenario: the wiring is read

- **Given** the Makefile and `qa-validate.yml`
- **When** the guard reads them
- **Then** the target runs `scripts/verify_closure.py` and the merge job calls `make verify-closure`
- **Test:** tests/test_verify_closure.py::test_the_check_is_wired_to_a_target_and_the_merge_job
