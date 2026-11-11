# archived-change-lifecycle

## ADDED Requirements

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
