# issue-triage

## ADDED Requirements

### Requirement: The implementer decides on the whole thread

The implementer's input MUST carry the issue's title, body and **every comment**
oldest-first with author and timestamp, plus the decision instruction, and a
read that fails MUST NOT produce an empty `issue.md`.

WHEN the implementer's input is rendered, THEN it contains the body, each comment
with its author and ISO8601Z stamp in order, the words that the body is the whole
thread when there are no comments, and the `TRIAGE` grammar; a failed read exits
non-zero.

#### Scenario: the thread carries every comment with its author and stamp

- **Given** an issue with two comments, the second superseding it
- **When** the thread is rendered
- **Then** the title, the body and both comments are present, oldest first, each with `@author` and its timestamp, and the render ends with the decision instruction
- **Test:** `tests/test_issue_triage.py::test_the_thread_carries_the_body_and_every_comment_with_author_and_stamp`

#### Scenario: an empty thread is said in words, an unreadable one fails

- **Given** an issue with no comments, and separately an issue that cannot be read
- **When** each is rendered
- **Then** the first says the body is the whole thread, and the second exits non-zero naming the failed read
- **Test:** `tests/test_issue_triage.py::test_an_issue_with_no_comments_says_so_and_an_unreadable_one_fails`

### Requirement: The verdict is applied deterministically, and refusals are loud

A single deterministic step MUST apply the implementer's verdict, and MUST write
nothing at all when the verdict is unusable.

WHEN `triage.md` carries `TRIAGE: implement`, THEN nothing is written and the run
continues; `TRIAGE: refine` with a restatement posts ONE comment and applies
`agent:refined`; `TRIAGE: close` with `EVIDENCE` and `REASON` posts the reason with
its evidence, closes the issue and applies `agent:closed`; a close with no
EVIDENCE, a refine with no restatement, and a missing/unknown verdict each exit 2
having written nothing.

#### Scenario: implement applies nothing

- **Given** a verdict of `implement`
- **When** it is applied
- **Then** the step exits 0 publishing `verdict=implement`, and no comment, label or close is issued
- **Test:** `tests/test_issue_triage.py::test_implement_applies_nothing`

#### Scenario: refine posts one restatement and labels

- **Given** a verdict of `refine` with a restatement
- **When** it is applied
- **Then** exactly one comment is posted carrying the restatement and the verdict marker, `agent:refined` is applied, the issue is not closed, and `verdict=refine` is published
- **Test:** `tests/test_issue_triage.py::test_refine_posts_one_restatement_and_labels_the_issue`

#### Scenario: close requires evidence

- **Given** a `close` verdict without an `EVIDENCE:` block
- **When** it is applied
- **Then** it exits non-zero saying the evidence is missing, and writes no comment, no close and no label
- **Test:** `tests/test_issue_triage.py::test_close_requires_evidence_and_posts_reason_with_it`

#### Scenario: close with evidence posts it and closes

- **Given** a `close` verdict with an `EVIDENCE:` block and a `REASON:`
- **When** it is applied
- **Then** the comment carries the reason and its evidence, the issue is closed, `agent:closed` is applied, and `verdict=close` is published
- **Test:** `tests/test_issue_triage.py::test_close_requires_evidence_and_posts_reason_with_it`

#### Scenario: an unreadable verdict is never guessed at

- **Given** no `TRIAGE:` line, an unknown `TRIAGE`, a `refine` with no restatement, and a missing file
- **When** each is applied
- **Then** every one exits non-zero saying REFUSED, and none writes to the issue
- **Test:** `tests/test_issue_triage.py::test_an_unreadable_verdict_is_never_guessed_at`

#### Scenario: a label that does not land is fatal

- **Given** a `gh` where `--add-label` silently applies nothing
- **When** a refine verdict is applied
- **Then** the run fails naming the label it could not apply, because the sweep reads that label to skip the issue
- **Test:** `tests/test_issue_triage.py::test_the_label_is_verified_not_assumed`

### Requirement: A decided issue is skipped through the shared queue rule

A verdict label MUST hold the issue from the sweep, and the rule MUST live in the
one queue implementation both bots read.

WHEN an issue carries `agent:refined` or `agent:closed`, THEN the shared queue
reports it out of the pick order with `reason=decided:<label>` and the next issue
takes `position=0`.

#### Scenario: a decided issue is not re-implemented

- **Given** the oldest issue carries `agent:refined` (and separately `agent:closed`)
- **When** the shared queue is built
- **Then** that issue is `impl_skip=1` with `reason=decided:<label>` and `position=-1`, `decided=<label>` is reported, and the next issue is at `position=0`
- **Test:** `tests/test_issue_review.py::test_a_decided_issue_is_skipped_by_the_shared_queue`

### Requirement: A refine or a close is a green outcome with no PR

The pipeline MUST NOT report a refine or a close as a failed implementation, and
MUST NOT continue to a PR for one.

WHEN the verdict is not `implement`, THEN the push, the PR, the fix loop, the
outcome comment and the "no implementation" red step are all skipped, the verdict
step sets `set -o pipefail` so its own failure cannot look green, and `triage.md`
is a scratch file that is never committed.

#### Scenario: the workflow renders the thread and applies the verdict

- **Given** the implementer pipeline
- **When** its steps are read
- **Then** the dispatch renders the thread through `make issue-thread` (the body-only read is gone), a step runs `make issue-verdict | tee … >> "$GITHUB_OUTPUT"` under `set -o pipefail`, and the push, outcome comment and red step are each gated on `steps.verdict.outputs.verdict == 'implement'`
- **Test:** `tests/test_issue_triage.py::test_the_workflow_renders_the_thread_and_applies_the_verdict`

#### Scenario: the scratch verdict is never committed

- **Given** `triage.md` is written by the implementer
- **When** the gitignore and the workflow's commit path are read
- **Then** `triage.md` is ignored and excluded from the commit, like `findings.md`
- **Test:** `tests/test_issue_triage.py::test_the_workflow_renders_the_thread_and_applies_the_verdict`
