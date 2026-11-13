# archived-change-lifecycle

## ADDED Requirements

### Requirement: The tree carries no fully-completed change left ACTIVE

After a keeper archive repair lands, the repository itself SHALL carry zero active changes
that are fully task-ticked while the issues they name are CLOSED — the five strays
`land-the-owed-rulebook-rows`, `the-owed-section-8-rows`, `captured-recipe-is-silent`,
`one-queue-reader`, `index-failure-names-its-cause` (issue #907) — and the repair SHALL be
archived as its own tracked change in the same commit, exactly as the 2026-11-12 precedent
(`archive-stranded-completed-changes`) did.

#### Scenario: the archive repair lands and the guard reads the tree clean

- **Given** the five completed-but-active changes on `master`
- **When** the keeper archive PR lands and `make openspec-archive-check` evaluates the tree
- **Then** it reads zero stranded changes and the five live under
  `openspec/changes/archive/` (moved, never deleted — rule 3b)
- **Test:** tests/test_openspec_archive_check.py::test_the_repository_itself_has_no_merged_change_left_active

#### Scenario: the generated index matches the disk after the move

- **Given** the five changes moved to `openspec/changes/archive/`
- **When** `make openspec-index-check` reads `OPENSPEC.md` against the tree
- **Then** every moved change is listed as archived and no active row survives for it
- **Test:** tests/test_openspec_index.py::test_real_repo_index_is_current_and_lists_every_change

#### Scenario: an archived change is left alone by the lifecycle gate

- **Given** the archive-repair change itself, moved under `openspec/changes/archive/` in the
  same commit
- **When** `make openspec-archive-check` evaluates the tree
- **Then** it is skipped like any archived change and never reported as active — the repair
  can never become the next stranded change
- **Test:** tests/test_openspec_archive_check.py::test_an_archived_change_is_left_alone
