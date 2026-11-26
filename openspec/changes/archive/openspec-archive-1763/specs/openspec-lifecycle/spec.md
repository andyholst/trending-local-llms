# openspec-lifecycle

## ADDED Requirements

### Requirement: An archive sweep is a tracked change

A PR that archives completed OpenSpec changes SHALL itself declare an OpenSpec change naming the
issue it closes; `make openspec-archive-check PR=<n>` MUST NOT report untracked work.

#### Scenario: the #1763 archive sweep

- **Given** the three completed #1747 changes archived with `PR: #1777`
- **When** `make openspec-archive-check PR=1777` runs
- **Then** the tracked `openspec-archive-1763` change binds the issue and the check passes
- **Test:** tests/test_openspec_archive_check.py::test_a_closed_issue_without_a_recorded_pr_is_a_violation
