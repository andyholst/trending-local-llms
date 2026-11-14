# openspec-backlog

## ADDED Requirements

### Requirement: The active OpenSpec backlog has a hard ceiling enforced at the merge gate

`make openspec-backlog-check` MUST count the directories under `openspec/changes/`
excluding `archive/` and, when that count reaches `MAX_ACTIVE_OPENSPEC_CHANGES` (50),
exit 1 naming every active change, its `Issue:` read from its `proposal.md`, and the
remedy command `make openspec-record-pr ISSUE=<n> PR=<pr>`. Under the cap it MUST print
`active=<n>/50` and exit 0. A missing `openspec/changes/` tree MUST be a loud exit 2,
never a vacuous clean. The check MUST be a prerequisite of `make openspec-check`, the
gate qa-validate runs on every PR and push, so an over-cap backlog blocks auto-merge to
`master`.

#### Scenario: the cap goes red

- **Given** a planted tree with exactly 50 active change directories and an archive/ dir
- **When** `scripts/openspec_backlog_check.py` runs against it
- **Then** it exits 1, lists every active change with its Issue, and prints the
  `openspec-record-pr` remedy
- **Test:** tests/test_openspec_backlog.py::test_exactly_at_the_cap_is_red

#### Scenario: headroom is visible, not silent

- **Given** a planted tree with 49 active changes
- **When** the check runs
- **Then** it exits 0 and prints `active=49/50`
- **Test:** tests/test_openspec_backlog.py::test_headroom_is_reported

#### Scenario: archive does not count

- **Given** a planted tree with 2 active changes and 60 archived ones under archive/
- **When** the check runs
- **Then** it reports active=2/50 and exits 0
- **Test:** tests/test_openspec_backlog.py::test_archived_changes_never_count

#### Scenario: a tree the check cannot read is never clean

- **Given** a fixture with no `openspec/changes/` directory at all
- **When** the check runs
- **Then** it exits 2 naming the missing tree
- **Test:** tests/test_openspec_backlog.py::test_missing_tree_is_loud

#### Scenario: the gate is wired where it bites

- **Given** the real Makefile and the real qa-validate workflow
- **When** the wiring test runs
- **Then** `openspec-backlog-check` is a prerequisite of `openspec-check` and
  `make openspec-check` is a step of qa-validate's `validate` job
- **Test:** tests/test_openspec_backlog.py::test_the_cap_gates_the_merge_pipeline
