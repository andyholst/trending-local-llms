## ADDED Requirements

### Requirement: Every issue closed by a PR is bound by a change
The change SHALL declare `Issue: #<n>` in its proposal so the OpenSpec lifecycle
guard (`scripts/openspec_archive_check.py`, `-pr` mode) finds the issue it closes
and does not report an untracked close.

#### Scenario: A closing PR has a change that names its issue
- **Given** an active change whose proposal declares `Issue: #1764` and `PR: fix/filer-label-rest-1764`
- **When** `make openspec-archive-check PR=1765` runs
- **Then** the guard binds Issue: #1764 and reports no `CLOSE of #1764`.
- **Test:** tests/test_openspec_binding.py::test_an_unbound_active_change_is_red
