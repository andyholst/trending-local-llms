# issue-bot-verdict

## ADDED Requirements

### Requirement: A `REFINED:` restatement is read whole and refused when cut

The verdict parser MUST read a `REFINED:` value as a sentence — continuation lines up to
the next key line or a blank line are joined — and MUST refuse, before any write, a value
that stops mid-sentence (on a word no sentence ends with, or on a trailing `,`/`-`/`—`/`(`).

#### Scenario: a restatement that wraps onto a second line

- **Given** a verdict whose `REFINED:` value continues on the following line and then `EVIDENCE:`
- **When** the verdict is parsed and applied
- **Then** the comment carries the WHOLE restatement, as one sentence
- **Test:** tests/test_issue_triage.py::test_a_wrapped_restatement_is_posted_whole

#### Scenario: the measured truncated restatement

- **Given** `REFINED: … cannot be implemented as written, and the` followed by `EVIDENCE:`
- **When** the verdict is applied
- **Then** it exits non-zero naming the cut, posts no comment and applies no label
- **Test:** tests/test_issue_triage.py::test_a_truncated_restatement_is_refused

#### Scenario: a short but complete restatement still passes

- **Given** `REFINED: scope it to the ROCm table only`
- **When** the verdict is applied
- **Then** it is accepted and one comment is posted (the guard is not a length gate)
- **Test:** tests/test_issue_triage.py::test_a_truncated_restatement_is_refused
