## ADDED Requirements

### Requirement: A completed change is archived in the change that lands the archive

Every OpenSpec change whose implementation merged (an open PR merged, or a
recorded `PR:` that merged) SHALL be moved to
`openspec/changes/archive/<date>-<name>/` by `make openspec-archive` in the
same PR that repairs the stranding, and the repair itself SHALL be recorded as
its own tracked change archived in that same commit — so an archive-repair
change can never itself become the next stranded active change.

#### Scenario: A merged-but-active change is repaired by a landing archive

- **Test:** tests/test_openspec_archive_check.py::test_the_repository_itself_has_no_merged_change_left_active
- **Given** an active change in `openspec/changes/` whose PR is merged
- **When** the archive repair PR lands on `master`
- **Then** `make openspec-archive-check` reads zero stranded changes, and the change lives under `openspec/changes/archive/` (moved, never deleted — rule 3b)

#### Scenario: An archived change is left alone by the lifecycle gate

- **Test:** tests/test_openspec_archive_check.py::test_an_archived_change_is_left_alone
- **Given** a change (including an archive-repair change) under `openspec/changes/archive/`
- **When** `make openspec-archive-check` evaluates the tree
- **Then** the archived change is skipped and never reported as active
