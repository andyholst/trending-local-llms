# pr-triggered-failure-ledger

## ADDED Requirements

### Requirement: a failure shape blocking two or more open pull requests is recorded once

`make pipeline-failure-issue` also walks the main pipelines' `pull_request`-triggered runs in its
window, groups them by a normalised failure shape, and for a shape that blocks at least
`PR_BLOCK_MIN_PRS` (2) OPEN pull requests files ONE issue for the group's earliest run and appends
its ledger row with the added keys `trigger`, `failure_shape`, `blocked_prs`, `pr_count`.

WHEN two or more open pull requests' main-pipeline runs concluded bad with the same failure shape
THEN one issue is filed for the group's earliest run, its ledger row names every blocked open PR,
and a second sweep files nothing more.

#### Scenario: one defect on two open PRs files once

- **Given** the stub `gh` timeline with `pull_request` runs 700 (`ci/a`), 701 (`ci/b`), 702 (`ci/merged`), 703 (`ci/c`), where 700/701/702 fail at `Prepare runner images` and 703 fails at `Run tests`, and open PRs `ci/a`, `ci/b`, `ci/c`
- **When** `make pipeline-failure-issue` sweeps
- **Then** exactly one PR-blockage issue is filed (run 700), its row names `blocked_prs == ["ci/a","ci/b"]`, `pr_count == 2`, a non-empty `failure_shape` and `trigger == "pull_request"`, and a second sweep files nothing more
- **Test:** `tests/test_pipeline_failure_issue.py::test_pr_blockage_pass_records_a_shared_failure_shape_once` — real filer, real stub `gh`

#### Scenario: run-specific tokens do not split one defect

- **Given** two error blocks identical except a run id and a SHA
- **When** `failure_shape` is computed for each
- **Then** both produce the same shape, while a different failing step or a different error block produces a different one
- **Test:** `tests/test_pipeline_failure_issue.py::test_failure_shape_groups_the_same_defect_and_separates_others` — real seam

#### Scenario: a merged branch and a lone PR are not a blockage

- **Given** a shape on one open PR, and the same shape also on a branch that is not an open PR
- **When** `group_pr_blockages` runs
- **Then** no group survives; an unreadable open-PR list (gh missing / a transport error) is an empty set, so nothing is recorded
- **Test:** `tests/test_pipeline_failure_issue.py::test_group_pr_blockages_needs_two_open_prs_and_drops_closed_branches` — real seam

#### Scenario: a dry run previews the filing and writes nothing

- **Given** the same scene, run with `--dry`
- **When** the sweep runs
- **Then** the output names the shape and both blocked PRs, and no issue and no ledger row is written
- **Test:** `tests/test_pipeline_failure_issue.py::test_pr_blockage_dry_run_previews_without_writing` — real filer

### Requirement: a recorded PR-blockage row whose fix never lands is red at the guard

`make pipeline-failure-guard-check` reports a `trigger: pull_request` row inside
`PR_BLOCK_GRACE_HOURS` (24 h) and REFUSES it past that grace when no `fix_pr` has landed; a row
with a landed fix PR and a collected guard clears through the normal attribution path.

WHEN a recorded PR-blockage row is older than the grace and names no fix PR
THEN the gate exits 1 naming the shape, the blocked PRs and the missing fix.

#### Scenario: both sides of the grace, on an injected clock

- **Given** a PR-blockage row filed 6 h ago and the same row filed 30 h ago, with `now` injected
- **When** the gate's verdict runs
- **Then** the 6 h row is reported with exit 0 and the 30 h row is refused with exit 1, and an ISO8601Z `filed_utc` is aged correctly rather than silently fresh
- **Test:** `tests/test_pipeline_failure_guard.py::test_a_recorded_pr_blockage_whose_fix_never_lands_is_red_after_its_grace` — real gate

#### Scenario: a landed fix clears the blockage and an unstamped row is untouched

- **Given** the same row carrying `fix_pr` + a guard test `make test` collects, and a master/schedule row with no `trigger`
- **When** the gate's verdict runs
- **Then** the fixed row is green and the master/schedule row is still the plain in-flight report
- **Test:** `tests/test_pipeline_failure_guard.py::test_a_recorded_pr_blockage_whose_fix_never_lands_is_red_after_its_grace` — real gate
