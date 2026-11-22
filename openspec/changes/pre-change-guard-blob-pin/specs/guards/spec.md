## ADDED Requirements

### Requirement: The pre-change blob is pinned by an immutable SHA

Both guard suites SHALL read the pre-change source from a SHA recorded in the test itself, never from a moving ref such as `origin/master`. A moving ref makes the negative assertion false on a full clone (the ref already has the feature) and vacuous in a checkout whose `git show` answers nothing.

#### Scenario: The rollup guard resolves its pinned pre-change blob

- **Given** `tests/test_engagement_rollup_1182.py` carries the pin `30c8f5f43500577e2f00af3d749e96b872650cdf` (the parent of the #1182 rollup commit `d4ad144`)
- **When** the guard reads `scripts/update_trending.py` at that SHA
- **Then** the blob resolves and carries `def recompute_7d_engagement(`
- **Test:** tests/test_engagement_rollup_1182.py::test_the_guard_is_red_on_the_pre_change_seam

#### Scenario: The stale_last_seen guard resolves its pinned pre-change blob

- **Given** `tests/test_stale_last_seen_gap.py` carries the pin `71b158aa0d30d8ec650af6f444fdfa1cbbd0879e` (the parent of the #1183 commit `6e71b2c`)
- **When** the guard reads `scripts/data_gap_analysis.py` at that SHA
- **Then** the blob resolves and is non-empty
- **Test:** tests/test_stale_last_seen_gap.py::test_the_guard_is_red_on_the_pre_change_analysis

### Requirement: An unresolvable pin fails loudly, never silently passes

A guard whose "old code is red" half cannot read the old code locks nothing. A failed or empty `git show` SHALL be a FAILED check, so a shallow clone, a pruned object or a container whose uid does not own the checkout is a loud red rather than a green built on empty output.

#### Scenario: A pin that cannot be resolved is refused

- **Given** the recorded SHA is absent from the repository (a shallow clone, a pruned object)
- **When** the guard reads the pre-change blob
- **Then** the check FAILS naming the SHA and the path, and the suite exits non-zero
- **Test:** tests/test_engagement_rollup_1182.py::test_the_guard_is_red_on_the_pre_change_seam

#### Scenario: A blob that no longer carries the probed seam is refused

- **Given** the pinned blob resolves but does not contain the function the guard slices
- **When** the guard slices the seam out of the blob
- **Then** the slice is never empty and the check FAILS loudly
- **Test:** tests/test_engagement_rollup_1182.py::test_the_guard_is_red_on_the_pre_change_seam

#### Scenario: The test container's uid does not own the checkout

- **Given** the suite runs in the test image, whose default user is uid 0 over a checkout owned by the invoking uid (issue #1147)
- **When** the guard reads the pinned blob
- **Then** the read still resolves, because `safe.directory` is passed on the command line rather than assumed
- **Test:** tests/test_engagement_rollup_1182.py::test_the_guard_is_red_on_the_pre_change_seam

### Requirement: The guard still proves the pre-change code lacks the feature

Pinning the blob SHALL NOT weaken the assertion: the pre-change body SHALL still be shown to lack the feature the change added.

#### Scenario: The rollup guard's assertion holds on the pinned blob

- **Given** the pinned pre-`d4ad144` blob
- **When** the guard slices `recompute_7d_engagement`
- **Then** the body contains neither the counter rollup nor the `19,516` figure
- **Test:** tests/test_engagement_rollup_1182.py::test_the_guard_is_red_on_the_pre_change_seam

#### Scenario: The stale_last_seen guard's assertion holds on the pinned blob

- **Given** the pinned pre-`6e71b2c` blob
- **When** the guard reads `scripts/data_gap_analysis.py`
- **Then** the module contains no `stale_last_seen` signal
- **Test:** tests/test_stale_last_seen_gap.py::test_the_guard_is_red_on_the_pre_change_analysis
