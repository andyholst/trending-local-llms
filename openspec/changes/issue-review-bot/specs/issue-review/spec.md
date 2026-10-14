# issue-review

## ADDED Requirements

### Requirement: ONE queue rule, read by both bots

The implementer's pick order — the OLDEST open `data-gap-analysis` issue that has
no `ci/data-gap-<n>-*` branch and no open PR from one — MUST be computed in ONE
place (`scripts/issue_queue.py`) and read by both pipelines through a make target
(`make issue-queue`), so the implementer and the reviewer can never disagree
about which issue is next.

WHEN either bot needs to know which issue is next,
THEN it runs `make issue-queue` and parses the machine-readable lines
(`issue=<n> position=<i> window=<open|closed> reason=<…> started=<0|1>`).

#### Scenario: the implementer picks through the shared queue

- **Given** the implementer workflow's `pick` job
- **When** its steps are read
- **Then** it checks out the repository and runs `make issue-queue`, and the branch/PR rule appears nowhere in the workflow
- **Test:** `tests/test_workflows.py::test_the_queue_rule_has_one_implementation`

#### Scenario: the reviewer imports the same queue

- **Given** `scripts/issue_review.py`
- **When** its source is read
- **Then** it imports `issue_queue` and derives the window from that module, never from a second copy of the rule
- **Test:** `tests/test_issue_review.py::test_the_reviewer_reads_the_one_queue_the_implementer_reads`

### Requirement: A 3 h quiet window on both sides of an implementer start

`REVIEW_GAP_HOURS` (3) is ONE constant. The reviewer MUST NOT write an issue's
body while an implementer run is in flight (the implementer's start comment is
posted before `make implement-issue`), while implementer activity on the issue is
younger than the window (start comment, outcome comment, branch commit, or the
PR's `createdAt`/`updatedAt`), or while the issue sits within the implementer's
next `REVIEW_GAP_HOURS` sweeps. The implementer's `pick` MUST defer to a fresh
reviewer marker (`<!-- issue-review: … run=<id> -->`, never a bare un-timestamped
label, which a cancelled run could leave behind for ever) so a refinement in
flight is never implemented mid-write.

WHEN the two bots' schedules overlap on one issue,
THEN only one of them writes it, and each defers to the other's marker.

#### Scenario: the boundary is the gap, not the wall clock

- **Given** a candidate whose implementer activity is 2 h 59 m old and, separately, 3 h 01 m old
- **When** the queue is built with the clock injected
- **Then** the first is `window=open reason=implementer-recent` and the second is `window=closed`
- **Test:** `tests/test_issue_review.py::test_the_window_opens_and_closes_at_the_three_hour_boundary`

#### Scenario: the window before a start is the queue position

- **Given** four candidates with no implementer, in createdAt order
- **When** the queue is built
- **Then** positions 0–2 are inside the window (`reason=next-sweep`) and position 3 is reviewable
- **Test:** `tests/test_issue_review.py::test_the_next_three_sweeps_are_the_window_before_a_start`

#### Scenario: the implementer defers to a reviewer's live window

- **Given** an issue carrying a fresh reviewer marker from another run
- **When** the queue is built for the implementer's pick
- **Then** that issue reports `impl_skip=1`, `position=-1` and `reason=reviewer-working`
- **Test:** `tests/test_issue_review.py::test_a_run_never_blocks_its_own_guard_but_another_run_does`

### Requirement: The implementer announces its window before it implements

`issue-bot.yml` MUST post ONE start comment (`<!-- issue-bot-start: <ISO8601Z>
-->`, naming the branch and the run) BEFORE `make implement-issue`, on both entry
paths, using the default token — a scheduled reviewer must never have to infer
from a run lookup whether a body is being read.

WHEN an implementer run starts on an issue,
THEN the issue carries a start comment naming that run before the body is read.

#### Scenario: the announcement precedes the implementation

- **Given** the implementer workflow's `implement` job
- **When** its steps are ordered
- **Then** the "Announce the window" step comes before the "Implement the issue" step, carries the marker, names the branch and the run, and uses `${{ github.token }}`
- **Test:** `tests/test_workflows.py::test_issue_bot_announces_its_window`

### Requirement: The reviewer never rewrites a body an implementer has read

On the `window` path the reviewer MUST write no body at all: the workflow writes
the rewritten body only when the body may be edited (the pick's `body` route plus
a passing guard re-check) and otherwise PROVES the body is byte-identical before
it replies. It replies at most ONCE per window and closes its marker when the run
ends.

WHEN an implementer has started on the picked issue,
THEN the run may post one bounded comment with evidence, and it must leave the
issue body unchanged.

#### Scenario: the body is proven untouched on the window path

- **Given** the reviewer workflow's `window` route
- **When** its steps are read
- **Then** `make review-issue-body-hash` is compared with the hash taken at the mark, a written `issue-body.md` is a loud failure, and the reply is gated by `make review-issue-guard … PATH=window`
- **Test:** `tests/test_workflows.py::test_issue_review_bot`

#### Scenario: one reply per window

- **Given** a started issue the reviewer has already answered inside this window
- **When** the reviewer picks again
- **Then** it reports `action=none reason=all-deferred` and posts no second reply
- **Test:** `tests/test_issue_review.py::test_pick_replies_once_to_a_started_implementer_and_then_goes_quiet`

### Requirement: The rewrite keeps every invisible marker

A refined body MUST keep every invisible HTML comment it carried
(`<!-- data-gap-signature: … -->`, `<!-- tech-debt-signature: … -->`) byte-identical:
they are the dedup keys the analysis and the findings filer search for, and
dropping one re-files an issue that already exists.

WHEN the refined body is about to be published,
THEN a missing marker from the live body fails the run loudly.

#### Scenario: a dropped marker fails the publish

- **Given** a live body carrying `<!-- tech-debt-signature: x -->` and a rewritten body without it
- **When** the marker check runs
- **Then** it exits non-zero and names the marker
- **Test:** `tests/test_workflows.py::test_issue_review_bot` (the `make review-issue-check-markers` step) and `tests/test_issue_review.py::test_mark_sets_the_label_and_never_writes_a_body_marker_for_the_window_path`

### Requirement: One run blocks nothing but other runs, and never itself

The reviewer's marker MUST carry the run that wrote it; a run's own marker MUST
NOT block its own guard re-check (the mark is written before the guard), while a
marker from another run MUST still defer it.

WHEN a run has already marked the issue it is reviewing,
THEN its guard re-check still passes, and another run reading the same marker is blocked.

#### Scenario: own marker passes, a foreign marker defers

- **Given** a marker written by `run=A` and a guard re-check from `run=A` (then from `run=B`)
- **When** each guard runs
- **Then** `run=A` gets `guard=ok` and `run=B` gets `guard=blocked reason=reviewed-recently`
- **Test:** `tests/test_issue_review.py::test_a_run_never_blocks_its_own_guard_but_another_run_does`

### Requirement: A review's findings become their own issues

Whatever the review notices MUST be filed as its own `tech-debt` issue through
the existing filing path (`make findings-check` + `make file-findings`), linked
to the issue it came from — never folded into the review, never fixed by the
reviewer, and never filed silently (a filing failure is loud).

WHEN a review produced findings,
THEN each one is an open `tech-debt` issue linked to the reviewed issue.

#### Scenario: the filing path is the shared one, and it is loud

- **Given** the reviewer workflow's filing step
- **When** it is read
- **Then** it runs `make findings-check` and `make file-findings`, with no `continue-on-error` and no `|| true`
- **Test:** `tests/test_workflows.py::test_issue_review_bot`

### Requirement: The reviewer never implements, pushes or merges

`.github/workflows/issue-review-bot.yml` MUST hold `issues: write` and
`contents: read` only, MUST NOT push, open a branch, open or merge a PR, and MUST
invoke every repo-logic step through a make target.

WHEN the reviewer workflow runs,
THEN nothing but issues (bodies, comments, labels, findings issues) changes.

#### Scenario: no write path beyond issues

- **Given** the reviewer workflow file
- **When** its permissions and run text are read
- **Then** it holds `issues: write` + `contents: read`, contains no `git push`, `gh pr create`, `gh pr merge`, `--admin` or `git checkout -b`, and evades no check with `|| true`
- **Test:** `tests/test_workflows.py::test_issue_review_bot`

#### Scenario: a silent review is a loud failure

- **Given** a review run that wrote no `comment.md`
- **When** the run's final step evaluates
- **Then** it exits non-zero, naming the missing summary
- **Test:** `tests/test_workflows.py::test_issue_review_bot`
