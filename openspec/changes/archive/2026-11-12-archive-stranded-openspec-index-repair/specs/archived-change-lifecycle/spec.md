## ADDED Requirements

### Requirement: A diagnosed stranding is repaired and archived within one landed change

When a merged PR leaves an OpenSpec change active, the repairing change SHALL
archive the stranded change AND its own record in the same landed commit, and
the master `validate` run SHALL return to green on the next push — the stranding
is closed by landing, not by filing.

#### Scenario: The stranded change is gone from the active tree after the repair lands

- **Test:** tests/test_openspec_archive_check.py::test_the_repository_itself_has_no_merged_change_left_active
- **Given** master carrying `openspec-index-repair` active with merged PR #859 (run 43269076958)
- **When** this repair PR lands and the next push-to-master `validate` runs
- **Then** `make openspec-archive-check` reads zero stranded changes and the run is green

#### Scenario: The archive-repair change never becomes the next stranding

- **Test:** tests/test_openspec_archive_check.py::test_an_archived_change_is_left_alone
- **Given** the repair change `archive-stranded-openspec-index-repair` with its `PR:` recorded
- **When** its own PR merges
- **Then** its record already sits under `openspec/changes/archive/` and the lifecycle gate skips it
