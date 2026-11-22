## ADDED Requirements

### Requirement: Pre-change guards use pinned blobs, never a moving ref

A rule-6c "old code is red" guard SHALL read its pre-change evidence from a
non-empty fixture pinned in the test file, not from `git show origin/master:…`
or any other ref whose content moves with master or is absent in a shallow
checkout. The fixture SHALL be the authentic pre-change body and SHALL be
refused loudly when empty or garbled.

#### Scenario: The rollup guard's pinned blob is authentic

- **Given** the `PRECHANGE_RECOMPUTE` fixture in `test_engagement_rollup_1182.py`
- **When** the authenticity guard runs
- **Then** it requires a non-empty `def recompute_7d_engagement(` body, and fails loudly otherwise
- **Test:** tests/test_engagement_rollup_1182.py::test_the_pre_change_fixture_is_authentic

#### Scenario: The rollup guard is red on the pinned old body

- **Given** the genuine pre-#1182 rollup body
- **When** the pre-change seam guard runs
- **Then** it confirms no post-counter rollup (`for counter in`, `19,516`) is present, for the same reason in CI and on a full clone
- **Test:** tests/test_engagement_rollup_1182.py::test_the_guard_is_red_on_the_pre_change_seam

#### Scenario: The analysis guard's pinned blob is authentic

- **Given** the `PRECHANGE_ANALYSE_EXCERPT` fixture in `test_stale_last_seen_gap.py`
- **When** the authenticity guard runs
- **Then** it requires a non-empty pre-#1183 gaps block, and fails loudly otherwise
- **Test:** tests/test_stale_last_seen_gap.py::test_the_pre_change_analysis_fixture_is_authentic

#### Scenario: The analysis guard is red on the pinned old body

- **Given** the genuine pre-#1183 gaps block
- **When** the pre-change analysis guard runs
- **Then** it confirms `stale_last_seen` is absent, for the same reason in CI and on a full clone
- **Test:** tests/test_stale_last_seen_gap.py::test_the_guard_is_red_on_the_pre_change_analysis

### Requirement: Both suites remain discovered and green

The new authenticity tests SHALL be invoked by each suite's `main()` so they
run under `make test` as well as pytest, and both suites SHALL pass without a
fetched `origin/master` ref.

#### Scenario: Wiring holds

- **Given** each suite's `main()`
- **When** the suite is invoked directly
- **Then** the authenticity and pre-change guards both run, and the suite reports `PASSED`
- **Test:** tests/test_engagement_rollup_1182.py::test_wiring

#### Scenario: No vacuous pass in a shallow checkout

- **Given** a tree with no `origin/master` ref
- **When** both suites run
- **Then** both pass because the fixtures are in-memory, rather than passing on empty `git show` output
- **Test:** tests/test_stale_last_seen_gap.py::test_wiring
