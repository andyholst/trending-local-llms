## ADDED Requirements

### Requirement: Stale targets are refused

The guard SHALL refuse a dispatch when the target issue is `CLOSED`, and SHALL refuse
when any PR bound to that issue is `MERGED` — including when the issue itself still
reads `OPEN`. The refusal SHALL name the reason (the closed state, or the PR number and
its merge time). A verdict SHALL be a pure function of the recorded issue/PR state, so
it is deterministic and offline-testable.

#### Scenario: An open issue with no bound PR is allowed

- **Given** an issue whose state is `OPEN` and no bound PR, and a lane count at or below the ceiling
- **When** `make dispatch-check ISSUE=<n>` runs
- **Then** it exits 0 and prints `ALLOW` together with `active_lanes=<count>/<ceiling>`
- **Test:** tests/test_dispatch_guard.py::test_open_issue_is_allowed

#### Scenario: A closed issue is refused

- **Given** an issue whose state is `CLOSED`
- **When** `make dispatch-check ISSUE=<n>` runs
- **Then** it exits non-zero and prints a reason naming `CLOSED`
- **Test:** tests/test_dispatch_guard.py::test_closed_issue_is_refused

#### Scenario: A merged bound PR is refused

- **Given** an `OPEN` issue bound to PR #1242 whose state is `MERGED` at `2026-11-23T13:19:42Z`
- **When** `make dispatch-check ISSUE=<n>` runs
- **Then** it exits non-zero and prints a reason naming PR #1242 and its merge
- **Test:** tests/test_dispatch_guard.py::test_merged_bound_pr_is_refused

### Requirement: Active lanes are bounded by one ceiling

The guard SHALL read the active-lane count from a caller-owned registry file that lives
OUTSIDE the repository, SHALL print that count on every verdict, and SHALL refuse when
the count is above ONE ceiling constant (`ACTIVE_LANE_CEILING`, default 3). An absent
registry SHALL count 0; a registry that cannot be read or parsed SHALL be undecidable
(exit 2), never a silent clean. A registry path that resolves inside the working tree
SHALL be refused, the same rule the watch monitor applies to its `--state` file.

#### Scenario: At and under the ceiling are allowed, over is refused

- **Given** the default ceiling 3 and counts 2, 3 and 4
- **When** the guard evaluates each count for an otherwise-open issue
- **Then** 2 and 3 are allowed, 4 is refused, and each verdict prints the count and ceiling
- **Test:** tests/test_dispatch_guard.py::test_concurrency_bound_is_one_constant

#### Scenario: The registry is outside the repository

- **Given** a caller-owned registry in a temporary directory and one that resolves inside the tree
- **When** the guard resolves both paths
- **Then** the outside path resolves and counts its lanes, and the in-repo path is refused
- **Test:** tests/test_dispatch_guard.py::test_registry_is_caller_owned_and_lives_outside_the_repo

### Requirement: The CLI and its help are deterministic and offline-testable

The script SHALL take `--issue`, `--registry`, `--ceiling`, `--repo`, `--from-file` and
`--json`; `--from-file` SHALL read a recorded issue/PR payload through the same state
shape the live `gh` reader produces, so the real decision code runs in tests with NO
network. `--help` SHALL document the registry path and the ceiling. Exit 0 = allowed,
1 = refused, 2 = undecidable. CREDENTIAL VALUES SHALL NOT appear in the script, its
fixtures or its output — only the key NAMES a live caller reads by.

#### Scenario: Real CLI over recorded fixtures

- **Given** local fixture files for open, closed, merged-PR, at-ceiling and over-ceiling
- **When** the real script runs on each fixture
- **Then** the exit codes are 0 for open/at-ceiling and non-zero for closed/merged-PR/over, with reasons on stdout
- **Test:** tests/test_dispatch_guard.py::test_cli_exit_codes_over_recorded_fixtures

#### Scenario: Help names the registry and the ceiling

- **Given** `python3 scripts/dispatch_guard.py --help`
- **When** it is run with no network
- **Then** it exits 0 and documents `--registry`, the outside-repository rule and `ACTIVE_LANE_CEILING = 3`
- **Test:** tests/test_dispatch_guard.py::test_help_documents_the_registry_and_the_ceiling

### Requirement: The make target is the caller's single seam

`make dispatch-check ISSUE=<n>` SHALL be the one target a planner or watcher consults
before spawning a lane. It SHALL forward the issue number, registry, ceiling and fixture
seam to the script, and SHALL exit non-zero on refusal with the guard's reason visible.

#### Scenario: The make target reports a refusal

- **Given** a recorded CLOSED issue and a caller-owned registry outside the repo
- **When** `make dispatch-check ISSUE=<n> REGISTRY=<path> FROM_FILE=<fixture>` runs
- **Then** it exits non-zero, prints `REFUSE` and the `CLOSED` reason; an open fixture exits 0
- **Test:** tests/test_dispatch_guard.py::test_make_dispatch_check_is_the_callers_single_seam
