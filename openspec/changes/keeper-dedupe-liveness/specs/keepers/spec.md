## ADDED Requirements

### Requirement: Only a LIVE keeper suppresses a duplicate

`keeper_dedupe` SHALL read each open keeper's `statusCheckRollup` beside its `mergeStateStatus` and count as suppressing ONLY a keeper whose required checks (`validate`, `live-smoke`) are green or still running. A mergeable keeper with no check objects, or with a concluded non-success check, SHALL be classified as a tombstone and SHALL NOT suppress.

#### Scenario: A green keeper suppresses

- **Given** an open mergeable keeper whose `validate` and `live-smoke` concluded `success`
- **When** the keeper sequence runs with `--dedupe`
- **Then** it exits 0 naming the existing keeper and files no branch
- **Test:** tests/test_keeper_pr.py::test_mergeable_keeper_suppresses_and_dirty_keeper_does_not

#### Scenario: A checkless mergeable keeper is a tombstone

- **Given** an open mergeable keeper whose head carries NO check objects (the PR #1248 shape)
- **When** the keeper sequence runs with `--dedupe`
- **Then** it names the keeper as a tombstone and files a fresh keeper against the current tip
- **Test:** tests/test_keeper_pr.py::test_a_checkless_mergeable_keeper_does_not_suppress

#### Scenario: A red keeper is a tombstone

- **Given** an open mergeable keeper whose `validate` concluded `failure`
- **When** the keeper sequence runs with `--dedupe`
- **Then** it names the keeper as a tombstone and files a fresh keeper
- **Test:** tests/test_keeper_pr.py::test_a_red_keeper_does_not_suppress

#### Scenario: A keeper still running is live

- **Given** an open mergeable keeper whose checks are `in_progress`
- **When** the keeper sequence runs with `--dedupe`
- **Then** it suppresses, so an in-flight repairer is never duplicated
- **Test:** tests/test_keeper_pr.py::test_an_in_flight_keeper_still_suppresses

### Requirement: A tombstone is named in the sweep log

A tombstone keeper SHALL be printed with the word `TOMBSTONE` and its branch, so the next machine reading the log can see why a fresh keeper was filed.

#### Scenario: The tombstone line

- **Given** a checkless mergeable keeper on the prefix
- **When** the dedupe runs
- **Then** the output names `TOMBSTONE` and the keeper's branch
- **Test:** tests/test_keeper_pr.py::test_a_checkless_mergeable_keeper_does_not_suppress
