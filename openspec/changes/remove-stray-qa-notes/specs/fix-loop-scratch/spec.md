# fix-loop-scratch

## ADDED Requirements

### Requirement: No scratch artifact of the fix loop is tracked by git

The repository MUST track no member of the loop's scratch class — `qa-report.txt`,
any `qa-report.txt.*` sibling, or `comment.md`. An ignore rule stops a NEW file from
being staged; it never untracks one, so the tracked tree itself is the invariant.

#### Scenario: the tree has a previously committed scratch file

- **Given** the repository at a commit whose tree carries `qa-report.txt.notes` (merged by PR #387, before the loop stopped creating it)
- **When** the tracked-scratch guard runs
- **Then** it fails and names the file, so the entry cannot survive a merge unnoticed
- **Test:** tests/test_fix_loop.py::test_no_scratch_report_file_is_tracked

#### Scenario: the scratch file is removed

- **Given** the file removed from the tracked tree with the working copy deleted
- **When** the guard runs again
- **Then** `git ls-files` finds nothing in the class and the guard passes
- **Test:** tests/test_fix_loop.py::test_no_scratch_report_file_is_tracked
