# archived-change-lifecycle Specification

## Purpose
TBD - created by archiving change archive-record-pr-774. Update Purpose after archive.

## Requirements

### Requirement: a merged-but-altive change is archived by the lifecycle guard

The OpenSpec lifecycle (rule 6f) MUST end a change whose issue is closed by
archiving that change — moving it under `openspec/changes/archive/` and
regenerating `OPENSPEC.md` — so `make openspec-archive-check` stays green on
`master`. A completing PR that closes an issue MUST NOT leave the change it
implemented active in `openspec/changes/`.

#### Scenario: a merged change left active turns the archive gate red on master

- **Given** a change whose `Issue:` is CLOSED (its completing PR merged) that still sits active under `openspec/changes/`
- **When** `make openspec-archive-check` runs
- **Then** it exits non-zero, names the change, and names the archive command (`make openspec-archive NAME=<change>` + `make openspec-index`)
- **And** after `make openspec-archive` + `make openspec-index`, the same check exits 0 and the change is only in `openspec/changes/archive/`
- **Test:** `tests/test_openspec_archive_check.py::test_an_archived_change_is_left_alone` and `tests/test_openspec_archive_check.py::test_a_closed_issue_without_a_recorded_pr_is_a_violation`

#### Scenario: archiving never deletes a completed change

- **Given** the completed `record-the-pr-on-a-change` change
- **When** it is archived
- **Then** its `proposal.md`/`spec.md`/`tasks.md` still exist under `openspec/changes/archive/` — nothing is removed, only moved and re-indexed (rule 3b)
- **Test:** `tests/test_openspec_archive_check.py::test_an_archived_change_is_left_alone`

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
