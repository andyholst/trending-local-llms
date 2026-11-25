# issue-filing Specification

## Purpose
TBD - created by archiving change issue-body-prefile-check-1730. Update Purpose after archive.

## Requirements

### Requirement: A filing lane validates its draft issue body before it files

Every fleet lane prompt that instructs the lane to file a GitHub issue SHALL instruct it to write the draft body to a file, run `make issue-message-check BODY_FILE=<draft>` on that file, and call `gh issue create` only when that check exits zero. The prompt SHALL name the command so no second parser is introduced.

#### Scenario: A declared body missing a section is refused before create

- **Given** a draft body carrying `message-pattern-opt-in` but omitting `## Technical Solution`
- **When** the filing lane runs `make issue-message-check BODY_FILE=<draft>`
- **Then** the check exits non-zero naming `## Technical Solution`, and the lane does not call `gh issue create`
- **Test:** tests/test_pr_message.py::test_declared_issue_is_validated_and_legacy_passes

#### Scenario: The filing prompts carry the pre-file step

- **Given** the filing lanes' prompt files in the tree
- **When** the wiring guard reads them
- **Then** each names `make issue-message-check BODY_FILE=` before its first `gh issue create`
- **Test:** tests/test_pr_message.py::test_a_filing_lane_validates_its_draft_issue_body_before_create

### Requirement: The seam the prompts name stays the one CI runs

`make issue-message-check` SHALL keep forwarding `BODY_FILE` to `scripts/pr_body.py --check-issue-file`, and the guard SHALL refuse a prompt that names a different validator.

#### Scenario: The Makefile and CLI seam are intact

- **Given** the Makefile and `scripts/pr_body.py` at the branch head
- **When** the wiring guard reads them
- **Then** `--check-issue-file "$(BODY_FILE)"` is present in the `issue-message-check` recipe and `--check-issue-file` is present in `pr_body.py`
- **Test:** tests/test_pr_message.py::test_a_filing_lane_validates_its_draft_issue_body_before_create

### Requirement: The rulebook row is owed, not silently written

The `AGENTS.md` §8 row naming the new guard SHALL be recorded as an owed row from a headless leg, with the task box marked blocked on rule 3c human sign-off.

#### Scenario: A headless leg does not edit the protected rulebook

- **Given** a headless implementation of this change
- **When** the leg records its analysis
- **Then** `findings/1730.md` carries an `- **Owed-row:**` marker for the `tests/test_pr_message.py` row and the task box is `- [~] … — blocked: rule 3c human sign-off`, with `AGENTS.md` byte-identical to the base
- **Test:** tests/test_file_findings.py::test_an_owed_row_finding_files_the_registered_marker
