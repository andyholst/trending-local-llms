# issue-queue-hold

## ADDED Requirements

### Requirement: An existing implementer branch holds its issue

The shared queue MUST treat an issue as already having an implementer — and so
MUST NOT offer it to a sweep — when a branch named
`ci/data-gap-<number>-<slug>` exists, matched against the FULL short ref the
GitHub API returns (`refs/heads/` stripped, the `ci/` segment intact). Every
other open issue in the same queue keeps its place.

WHEN the queue is read and an issue has a `ci/data-gap-<n>-*` branch,
THEN that issue is absent from the candidates and its neighbours are unchanged.

#### Scenario: an issue with an implementer branch is not a candidate

- **Given** a `gh` answering `[{"ref": "refs/heads/ci/data-gap-176-tech-debt-a-repair-in-flight"}]`
- **When** `scripts/issue_queue.py` prints the queue
- **Then** no `issue=176` row is printed, and the issues without a branch are still offered
- **Test:** `tests/test_issue_review.py::test_a_ci_data_gap_branch_holds_its_issue`

#### Scenario: an empty ref list still offers every issue

- **Given** a `gh` whose ref read answers `[]`
- **When** the queue is printed
- **Then** every open candidate is offered, exactly as before this change
- **Test:** `tests/test_issue_review.py::test_the_queue_reads_both_labels_as_one_oldest_first_list`

### Requirement: A failed branch read is loud, never a silent "no implementer"

When the ref read fails, the queue MUST print one `[issue-queue] WARN:` line on
STDERR naming the `ci/data-gap-*` read and the hold it degrades, MUST keep
running (the other holds are unaffected), and MUST NOT put that warning on the
machine-readable STDOUT a workflow parses.

WHEN `gh` fails the `matching-refs` read,
THEN the queue still prints its candidates, and stderr carries the warning.

#### Scenario: a failed ref read warns without reaching stdout

- **Given** a `gh` that exits non-zero for `/git/matching-refs/`
- **When** the queue is printed
- **Then** it exits 0, stderr names the branch read and the hold, and stdout carries no warning
- **Test:** `tests/test_issue_review.py::test_a_failed_branch_read_is_loud_never_silent`
