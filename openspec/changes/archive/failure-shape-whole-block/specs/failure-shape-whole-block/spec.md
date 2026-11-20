# failure-shape-whole-block

## ADDED Requirements

### Requirement: the failure shape digests the whole bounded error block

`scripts/pipeline_failure_issue.py::failure_shape` derives its digest from every line of the
error block it is given, not from a leading slice. Two failed runs are the SAME failure only when
their whole bounded blocks normalise alike.

WHEN two failed runs share an opening and differ later in the block
THEN they are two shapes, and the same block twice is one shape.

#### Scenario: two same-prefix failures are two shapes

- **Given** two error blocks identical through the first eight normalised lines and differing after them, with the same failing step and `make` targets
- **When** `failure_shape` digests each
- **Then** the digests differ
- **Test:** `tests/test_pipeline_failure_issue.py::test_failure_shape_groups_the_same_defect_and_separates_others` — real seam

#### Scenario: the same block is still one shape

- **Given** one error block digested twice with the same step and targets
- **When** `failure_shape` runs
- **Then** the digests are equal, so one defect on two PRs still groups
- **Test:** `tests/test_pipeline_failure_issue.py::test_failure_shape_groups_the_same_defect_and_separates_others` — real seam

#### Scenario: the guard is red on the pre-change seam

- **Given** `origin/master`'s `scripts/pipeline_failure_issue.py` (`skeleton[:8]`)
- **When** the module runs against it
- **Then** the two-shape check and the no-prefix-slice check FAIL
- **Test:** `tests/test_pipeline_failure_issue.py::test_failure_shape_groups_the_same_defect_and_separates_others` — measured `226 passed, 2 failed` on the old seam
