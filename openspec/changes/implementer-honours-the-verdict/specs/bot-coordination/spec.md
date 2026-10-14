# bot-coordination

## ADDED Requirements

### Requirement: A reviewer verdict holds the implementer while it is fresh

The reviewer's verdict label (`needs-refinement`, and the `obsolete` /
`duplicate` / `already-fixed` family) MUST hold the implementer off that issue
while it is FRESH, and MUST NOT hold it for ever: a label carries no timestamp, so
freshness MUST come from the newest reviewer marker comment on the issue
(`<!-- issue-review: … -->`, including a window reply). `VERDICT_TTL_HOURS` (24)
is the boundary, and the rule lives in the ONE queue both bots read
(`scripts/issue_queue.py`, `make issue-queue`) — never in a workflow file.

WHEN the shared queue evaluates an open issue carrying a verdict label,
THEN a verdict whose newest reviewer marker is younger than `VERDICT_TTL_HOURS`
holds the implementer (`impl_skip=1`, `reason=verdict-fresh`, `position=-1`) and
reports `verdict` / `verdict_since` / `verdict_fresh`; an older marker releases
the issue (still reporting the verdict); and a label with no reviewer marker at
all is reported and never holds.

#### Scenario: a fresh verdict holds the implementer

- **Given** the oldest open `data-gap-analysis` issue carries `needs-refinement` and a reviewer marker comment two hours old
- **When** the shared queue is built at that instant
- **Then** its row is `impl_skip=1 reason=verdict-fresh position=-1` with `verdict=needs-refinement` and `verdict_since=<that marker>`, and the NEXT issue is the one at `position=0`
- **Test:** `tests/test_issue_review.py::test_a_fresh_verdict_holds_the_implementer`

#### Scenario: a stale verdict releases the issue

- **Given** the same label with a reviewer marker 25 hours old (a label left by a cancelled run)
- **When** the queue is built
- **Then** the issue is back at `position=0` with `impl_skip=0` and `verdict_fresh=0`, and the verdict is still reported in its row
- **Test:** `tests/test_issue_review.py::test_a_stale_verdict_releases_the_issue`

#### Scenario: a label with no reviewer marker never holds

- **Given** an issue carrying a verdict label and no reviewer comment at all
- **When** the queue is built
- **Then** `verdict` is reported, `verdict_since=none`, and the issue is not held
- **Test:** `tests/test_issue_review.py::test_a_label_without_any_reviewer_marker_never_holds`

### Requirement: The implementer answers a verdict with a comment, once per round

When the sweep's `pick` job finds nothing to implement because a fresh verdict
holds the queue, it MUST say so ON the held issue — one comment, carrying the
verdict and the reviewer's own timestamp — and MUST NOT write a label or edit a
body: the verdict belongs to the reviewer or a human.

WHEN the pick comes back empty and a fresh verdict holds an issue,
THEN `make issue-skip-note` (`scripts/issue_queue.py --skip-note`) posts exactly
one comment on the oldest held issue with the marker
`<!-- issue-bot-skip: <ISO8601Z> verdict=<label> since=<reviewer ts> -->`, and a
second run in the SAME review round posts nothing.

#### Scenario: the skip note is posted once per review round

- **Given** a held issue with no skip note and the sweep's pick empty
- **When** `make issue-skip-note` runs
- **Then** one comment is posted on that issue carrying `issue-bot-skip: … verdict=needs-refinement since=<that marker>`, and a second run in the same round posts nothing (`already noted`)
- **Test:** `tests/test_issue_review.py::test_skip_note_is_posted_once_per_review_round`

#### Scenario: skipping never edits a label or a body

- **Given** a held issue
- **When** the skip note runs
- **Then** the only write it performs is one `gh issue comment` — no `issue edit`, no label call
- **Test:** `tests/test_issue_review.py::test_the_implementer_never_edits_a_label_or_a_body_when_it_skips`

#### Scenario: an empty pick is what triggers the note

- **Given** the implementer pipeline's `pick` job
- **When** its steps are read
- **Then** the verdict step runs `make issue-skip-note` only when the pick came back empty, sets `GH_TOKEN` to the default token (the owner PAT cannot comment), and its run block writes no label
- **Test:** `tests/test_workflows.py::test_issue_bot`

### Requirement: The queue rule keeps exactly one implementation

The branch/PR rule, the 3 h reviewer window and the fresh-verdict hold MUST be
computed in one place and read by both bots through `make issue-queue`; a second
copy in a workflow file is the defect this requirement forbids.

WHEN either bot needs to know whether it may touch an issue,
THEN it runs `make issue-queue` and parses its machine-readable lines, and the
rule appears in no second script and in no workflow step.

#### Scenario: the rule is not duplicated

- **Given** the two bot workflows and the repository
- **When** the queue rule is searched for
- **Then** it exists once (in `scripts/issue_queue.py`, reached through `make issue-queue`), and the workflows only parse its lines
- **Test:** `tests/test_workflows.py::test_the_queue_rule_has_one_implementation`
