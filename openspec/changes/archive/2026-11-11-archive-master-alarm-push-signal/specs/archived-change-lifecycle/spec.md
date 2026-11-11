# archived-change-lifecycle

## ADDED Requirements

### Requirement: an archive change archives its own record in the same commit

A change whose entire work is the archiving of other changes MUST archive its
own directory in the same commit: an ACTIVE change naming a PR that merges it
is the exact state `make openspec-archive-check` reds on the next master push,
and an archive PR must not manufacture its own recurrence.

#### Scenario: a finished archive change does not stay active after its PR merges

- **Given** a change whose only work is `make openspec-archive NAME=<stale>` + `make openspec-index`
- **When** its completing PR is prepared
- **Then** the change directory itself sits under `openspec/changes/archive/` in that same commit, and `OPENSPEC.md` lists both entries
- **And** `make openspec-archive-check` on the merge candidate exits 0 (no active change names a merged PR or closed issue)
- **Test:** `tests/test_openspec_archive_check.py::test_the_repository_itself_has_no_merged_change_left_active` and `tests/test_openspec_archive_check.py::test_an_archived_change_is_left_alone`
