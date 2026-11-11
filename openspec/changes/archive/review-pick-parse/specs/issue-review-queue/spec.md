# issue-review-queue

## ADDED Requirements

### Requirement: `--pick`'s machine-readable `issue=` line carries the number only

`make review-issue-pick` MUST print candidate diagnostics on a line that no key
parser claims (`candidate=<n> position=…`), and the ONLY line beginning with
`issue=` MUST be the action's, whose value is the issue number with no
diagnostics. This MUST hold for a four-candidate queue where every candidate is
deferred (the shape that broke run 39040689085).

#### Scenario: four candidates, one of them reviewable

- **Given** four labelled issues, three inside an implementer window and one outside
- **When** `scripts/issue_review.py --pick` runs
- **Then** exactly one line starts with `issue=` and it is `issue=176`
- **Test:** tests/test_issue_review.py::test_the_pick_output_the_workflow_parses_is_a_number

#### Scenario: every candidate deferred

- **Given** four candidates all inside a window
- **When** `--pick` runs
- **Then** the `issue=` line is empty and no diagnostic rides on it
- **Test:** tests/test_issue_review.py::test_the_pick_output_the_workflow_parses_is_a_number

### Requirement: The workflow's own parser extracts the number from the real pick output

The shipped `Pick ONE issue to review` step MUST yield `issue=<digits>` in
`$GITHUB_OUTPUT` when fed the real `--pick` stdout, MUST read only the FIRST token of
a key so the pre-fix shape (diagnostics riding on the `issue=` line) can no longer
poison it, and MUST fail loudly on a value that is not numeric at all.

#### Scenario: the real output through the shipped step

- **Given** the workflow's own `run:` block and a `make` that prints the real `--pick` output
- **When** the step executes with a `$GITHUB_OUTPUT` file
- **Then** `issue=176` is written, matching `^[0-9]+$`
- **Test:** tests/test_issue_review.py::test_the_pick_output_the_workflow_parses_is_a_number

#### Scenario: the pre-fix shape can no longer poison ISSUE

- **Given** the pre-fix line `issue=266 position=-1 window=open reason=…`
- **When** the shipped step parses it
- **Then** `issue=266` is written — the number, never the tail
- **Test:** tests/test_issue_review.py::test_the_pick_output_the_workflow_parses_is_a_number

#### Scenario: a non-numeric value is refused

- **Given** `issue=not-a-number` on the action line
- **When** the shipped step parses it
- **Then** it exits non-zero with an error naming the non-numeric value
- **Test:** tests/test_issue_review.py::test_the_pick_output_the_workflow_parses_is_a_number

### Requirement: A reviewer target refuses a non-numeric ISSUE

Every `review-issue-*` target that takes `ISSUE=` MUST refuse a value containing
anything but digits, exiting non-zero with a message naming the parse defect,
instead of reaching argparse's `unrecognized arguments`.

#### Scenario: the measured failure value

- **Given** `ISSUE="266 position=-1 window=open reason=decided:agent:refined"`
- **When** `make review-issue-finish` runs
- **Then** it exits non-zero and its output says the value must be the number
- **Test:** tests/test_issue_review.py::test_a_reviewer_target_refuses_a_non_numeric_issue

### Requirement: A failed thread step stops the steps that consume its value

The step that writes `issue.md` MUST carry an id, and every later step that reads
`ISSUE` or the thread MUST be gated on that step's success; the `always()` window
close MUST be gated on the window-open step's success, so a run that never opened a
window never tries to close one.

#### Scenario: the thread step fails

- **Given** the reviewer pipeline
- **When** `Write the issue and its comments` fails
- **Then** the mark/route/refine/reply/findings steps are skipped and the run has one failure
- **Test:** tests/test_workflows.py::test_issue_review_bot
