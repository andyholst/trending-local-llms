# issue-queue

## ADDED Requirements

### Requirement: Every verdict-held issue is announced, once per round

`make issue-skip-note` MUST post one note per issue the queue reports as held by a
fresh reviewer verdict (bounded), each carrying that issue's own `since=`, and MUST
post nothing further for a round that is already noted.

#### Scenario: two issues are held by fresh verdicts

- **Given** two issues, each with a verdict label and its own fresh reviewer marker
- **When** `--skip-note` runs
- **Then** exactly two comments are posted, one per issue, each carrying its own `since=`, and the run reports `2 posted`
- **Test:** tests/test_issue_review.py::test_the_skip_note_covers_every_held_issue

#### Scenario: the same round runs again

- **Given** both notes are now on their issues
- **When** `--skip-note` runs again in the same round
- **Then** no additional comment is posted and the run reports them as already noted
- **Test:** tests/test_issue_review.py::test_the_skip_note_covers_every_held_issue

### Requirement: The walk is bounded and says what it left

The note walk MUST stop after `MAX_SKIP_NOTES` issues and report how many held issues
remain for the next sweep, so a backlog is neither a comment storm nor a silent gap.

#### Scenario: more issues are held than the bound

- **Given** more held issues than `MAX_SKIP_NOTES`
- **When** `--skip-note` runs
- **Then** it notes at most the bound and prints how many remain
- **Test:** tests/test_issue_review.py::test_the_skip_note_covers_every_held_issue
