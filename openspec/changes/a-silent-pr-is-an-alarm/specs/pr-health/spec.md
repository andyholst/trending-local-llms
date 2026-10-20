# pr-health

## ADDED Requirements

### Requirement: A silent open PR is reported and made loud

The sweep MUST flag every OPEN, non-draft PR that is `CONFLICTING`/`DIRTY` or whose head commit
has no check runs, MUST name the head branch and the fix, and MUST exit 1 when any PR is silent.

#### Scenario: a conflicting PR

- **Given** an open PR reported `CONFLICTING` with no runs on its head commit
- **When** the sweep runs
- **Then** it exits 1, names the PR and its head branch, and says no workflow can run
- **Test:** tests/test_pr_health.py::test_a_conflicting_pr_is_silent_and_named

#### Scenario: a healthy PR

- **Given** a mergeable PR with runs on its head commit
- **When** the sweep runs
- **Then** it exits 0 and reports nothing silent
- **Test:** tests/test_pr_health.py::test_a_healthy_pr_is_not_flagged

#### Scenario: a pipeline that never started

- **Given** a mergeable PR with NO runs
- **When** the sweep runs
- **Then** it exits 1 with the missing-runs reason and no conflict claim
- **Test:** tests/test_pr_health.py::test_a_pr_whose_pipeline_never_started_is_flagged_too

#### Scenario: a draft

- **Given** a draft PR, conflicting and quiet
- **When** the sweep runs
- **Then** it is not flagged and not counted
- **Test:** tests/test_pr_health.py::test_drafts_are_left_alone

### Requirement: The flag names the fix and is posted once

With `--comment`, the sweep MUST leave ONE note per affected PR naming the resume and the push
shape, and MUST NOT comment a second time while its marker is present.

#### Scenario: the comment

- **Given** a silent PR and `--comment`
- **When** the first sweep runs
- **Then** it posts the marker note containing `make worktree-resume` and `refs/heads/<PR head>`
- **Test:** tests/test_pr_health.py::test_the_comment_carries_the_fix_and_is_deduplicated

#### Scenario: the second sweep

- **Given** the same PR, whose thread already carries the marker
- **When** the sweep runs again
- **Then** it reports "already flagged" and posts nothing
- **Test:** tests/test_pr_health.py::test_the_comment_carries_the_fix_and_is_deduplicated

### Requirement: An unreadable state is loud

A `gh` failure MUST exit 2 and quote the tool's own message.

#### Scenario: gh fails

- **Given** a `gh` that exits 1
- **When** the sweep runs
- **Then** it exits 2 and quotes the failure
- **Test:** tests/test_pr_health.py::test_a_gh_failure_is_loud

### Requirement: The sweep is wired to a target, a pipeline and a guard

`make pr-health` MUST run the script, `pr-health.yml` MUST call it through the Makefile with a
first-job guard, and the cron-only pipeline MUST be classified in the coverage map.

#### Scenario: the wiring is read

- **Given** the Makefile, the workflow, `BOT_GUARDS` and `DISPATCH_ONLY_COVERAGE`
- **When** the guard reads them
- **Then** all four are present, the guard precedes the sweep, and the comment uses the default token
- **Test:** tests/test_pr_health.py::test_the_sweep_is_wired_to_a_target_a_workflow_and_a_guard
