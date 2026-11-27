## ADDED Requirements

### Requirement: The architect filing prompt validates its draft body before create

The `tll-architect` filing prompt SHALL instruct the lane to write the complete issue body to a draft file, run `make issue-message-check BODY_FILE=<draft>` on it, and call `gh issue create` only when that verdict is zero, naming the same command the other filing lanes use (issue #1814, extending #1730).

#### Scenario: An opt-in draft missing a section blocks the filing

- **Given** a draft body carrying `message-pattern-opt-in` but omitting `## Technical Solution`
- **When** the architect lane runs `make issue-message-check BODY_FILE=<draft>`
- **Then** the check exits non-zero naming the missing section, and the lane does not call `gh issue create`
- **Test:** tests/test_pr_message.py::test_declared_issue_is_validated_and_legacy_passes

#### Scenario: Every filing prompt including the architect names the pre-file seam

- **Given** the filing lane prompts in the tree
- **When** the wiring guard reads each prompt named by `FILING_LANE_PROMPTS`
- **Then** each names `make issue-message-check BODY_FILE=` before its first `gh issue create`
- **Test:** tests/test_pr_message.py::test_a_filing_lane_validates_its_draft_issue_body_before_create

### Requirement: The single validator seam stays intact

`make issue-message-check` SHALL keep forwarding `BODY_FILE` to `scripts/pr_body.py --check-issue-file`, and the guard SHALL pin that seam so no second parser is introduced for the added lane.

#### Scenario: Makefile and CLI still own the one issue-body check

- **Given** the Makefile and `scripts/pr_body.py` at the branch head
- **When** the wiring guard reads them
- **Then** `--check-issue-file "$(BODY_FILE)"` is present in the `issue-message-check` recipe and `--check-issue-file` is present in `pr_body.py`
- **Test:** tests/test_pr_message.py::test_a_filing_lane_validates_its_draft_issue_body_before_create
