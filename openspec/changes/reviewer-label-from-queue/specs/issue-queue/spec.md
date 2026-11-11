## ADDED Requirements

### Requirement: The issue-queue label has ONE definition and no reader may re-spell it

The reviewer label and the gap filer label are the queue's first label, read from
`scripts/issue_queue.py::QUEUE_LABELS` — never a second or third literal copy of the
same string in another script (rule 6j/6d: the label set is ONE list, not one per bot).

#### Scenario: a reader script carries no private copy of the queue label

- **Given** the `scripts/` directory
- **When** the tracked scripts are scanned for the literal `"data-gap-analysis"`
- **Then** only `scripts/issue_queue.py` (the definition) carries it
- **And** `scripts/issue_review.py` and `scripts/data_gap_analysis.py` do not
- **Test:** tests/test_issue_review.py::test_the_queue_label_has_one_definition_and_no_reader_copy

#### Scenario: both readers resolve the queue's own first label

- **Given** the real `scripts/data_gap_analysis.py` and the real
  `scripts/issue_review.py::decide()` driving the real `scripts/issue_queue.py`
  (stubbed `gh` as the external system only)
- **When** each is asked which label it reads
- **Then** each equals `issue_queue.QUEUE_LABELS[0]`
- **Test:** tests/test_issue_review.py::test_the_reviewer_and_the_filer_resolve_the_queue_label
