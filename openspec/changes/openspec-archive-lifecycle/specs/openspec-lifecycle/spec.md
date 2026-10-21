# openspec-lifecycle

## ADDED Requirements

### Requirement: The lifecycle states when a change is archived

`ARCHITECTURE.md` §8 (the life of a change) MUST state the end state of a change:
once the PR named on its `PR:` line is merged, the change moves to
`openspec/changes/archive/<name>` through `make openspec-archive NAME=<change>`,
and the same PR regenerates `OPENSPEC.md` (`make openspec-index`) so the change is
listed as archived in one commit. It MUST also name the guard that enforces it.

#### Scenario: the description names the archive step

- **Given** the repository's `ARCHITECTURE.md`
- **When** a reader looks at the life of a change (§8)
- **Then** it names `make openspec-archive NAME=<change>`, says the archive happens in the PR that completes the change, requires `make openspec-index` in that same PR, and names `make openspec-archive-check`
- **Test:** `tests/test_openspec_archive_check.py::test_the_description_documents_when_a_change_is_archived`

### Requirement: An active change never names a merged PR

`make openspec-archive-check` (`scripts/openspec_archive_check.py`) MUST fail
when an ACTIVE change's `PR:` line names a merged pull request, and MUST name the
change, the PR and the two commands that fix it. A change with no `PR:` line is
skipped (nothing to assert), and an ARCHIVED change naming a merged PR is the
expected state, never a finding.

#### Scenario: a merged PR left an active change behind

- **Given** an active change whose proposal says `PR: #42` and a `gh` that reports PR #42 as merged
- **When** `make openspec-archive-check` runs
- **Then** it exits 1 and names the change, `#42` and `make openspec-archive NAME=<change>`
- **Test:** `tests/test_openspec_archive_check.py::test_a_merged_pr_left_an_active_change_behind`

#### Scenario: an unmerged PR is not a violation

- **Given** an active change whose `PR:` line names an open pull request
- **When** the check runs
- **Then** it exits 0, because the change is still in flight
- **Test:** `tests/test_openspec_archive_check.py::test_an_unmerged_pr_is_not_a_violation`

#### Scenario: an archived change is left alone

- **Given** a change under `openspec/changes/archive/` whose `PR:` line names a merged PR
- **When** the check runs
- **Then** it exits 0: its lifecycle is complete
- **Test:** `tests/test_openspec_archive_check.py::test_an_archived_change_is_left_alone`

### Requirement: The lifecycle guard fails loudly when it cannot see a PR's state

A GitHub read that fails MUST make the check exit 2 with the reason, never pass
as if the state were known; the repository argument comes from `--repo`, else
`GITHUB_REPOSITORY`, else `gh`'s own resolution.

#### Scenario: gh is unavailable or refused

- **Given** a change with a `PR:` line and a `gh` that exits non-zero
- **When** the check runs
- **Then** it exits 2 and prints what `gh` reported
- **Test:** `tests/test_openspec_archive_check.py::test_a_gh_failure_is_loud`

#### Scenario: the guard is wired to CI

- **Given** the Makefile and `qa-validate.yml`
- **When** the wiring is inspected
- **Then** `make openspec-archive-check` exists and `qa-validate`'s `validate` job calls it with a token that can read pull requests
- **Test:** `tests/test_openspec_archive_check.py::test_the_guard_is_wired_to_a_target_a_workflow_and_the_gate`
