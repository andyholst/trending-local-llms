# issue-review-queue

## ADDED Requirements

### Requirement: The queue producer prints the one line a sweep reads

`make issue-pick` MUST print exactly one line — `issue=<n>` for the head of the pick
order, or `issue=` when nothing is takeable — with every explanatory line on stderr, so
no workflow has to re-derive the value from the queue row.

#### Scenario: a backlog with a takeable issue

- **Given** four labelled issues with no implementer and no reviewer hold
- **When** `scripts/issue_queue.py --pick` runs
- **Then** stdout is exactly one line, `issue=163`, and the reason it was chosen is on stderr
- **Test:** tests/test_issue_review.py::test_the_sweep_reads_the_producers_own_pick_line

#### Scenario: an empty backlog

- **Given** every labelled issue has an implementer or a fresh verdict hold
- **When** `--pick` runs
- **Then** it prints `issue=` and says on stderr why each issue was skipped
- **Test:** tests/test_issue_review.py::test_the_sweep_reads_the_producers_own_pick_line

### Requirement: A value outside the token shape is refused by the producer

`checked(key, value, allowed=…)` MUST refuse — exit non-zero, naming the key and the raw
value — any value carrying whitespace (or a character outside the token shape), and any
enumerated value outside its set. It MUST return a legitimate token unchanged.

#### Scenario: a value a whitespace-splitting reader would truncate

- **Given** `reason` = `window open`
- **When** `checked("reason", "window open")` is called
- **Then** it exits non-zero with a message naming `reason` and the raw value
- **Test:** tests/test_issue_review.py::test_a_value_outside_the_token_shape_is_refused_by_the_producer

#### Scenario: a legitimate token

- **Given** `reason` = `window-open:open` and `issue` = `163`
- **When** each is checked
- **Then** both are returned unchanged
- **Test:** tests/test_issue_review.py::test_a_value_outside_the_token_shape_is_refused_by_the_producer

### Requirement: Each workflow reads its producer's value whole, and fails loudly on a bad shape

The implementer's pick step MUST copy the value the producer named (no `sed`/`awk` of
the row) and refuse a non-numeric value; the reviewer's pick step MUST take each value
whole (no whitespace split) and refuse a value carrying whitespace, naming the key.

#### Scenario: the sweep's shipped step reads the real pick

- **Given** the shipped `Pick the oldest …` run block and a `make` that prints the real `--pick` stdout
- **When** the step executes with a `$GITHUB_OUTPUT` file
- **Then** `issue=163` is written and the step exits 0
- **Test:** tests/test_issue_review.py::test_the_sweep_reads_the_producers_own_pick_line

#### Scenario: a non-numeric pick

- **Given** a producer line of `issue=not-a-number`
- **When** the shipped sweep step parses it
- **Then** the step fails with an error naming the value
- **Test:** tests/test_issue_review.py::test_the_sweep_reads_the_producers_own_pick_line

#### Scenario: the reviewer's shipped step refuses a whitespace value

- **Given** the pre-fix shape `issue=266 position=-1 window=open reason=…`
- **When** the shipped reviewer step parses it
- **Then** it fails with `carries whitespace`, never writing a truncated `issue=266`
- **Test:** tests/test_issue_review.py::test_the_pick_output_the_workflow_parses_is_a_number
