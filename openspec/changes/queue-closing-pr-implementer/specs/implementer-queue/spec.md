## ADDED Requirements

### Requirement: A closing PR marks its issue as implemented, whatever its branch is named

`issue_queue.build` SHALL mark an issue as having an implementer when any OPEN pull request's body binds a closing keyword to that issue number, regardless of the PR's `headRefName`. The binding SHALL be read through `scripts/pr_closure.py`'s closure parser — the ONE implementation — never a second copy of the keyword list.

#### Scenario: A `fix/`-prefixed PR closes the issue

- **Given** an open PR on branch `fix/pr-block-grace-derived-1176` whose body carries one `closes #1176`
- **When** `make issue-queue` builds the queue
- **Then** #1176 is NOT offered as `next-sweep` — it has an implementer
- **Test:** tests/test_issue_review.py::test_a_closing_pr_marks_its_issue_implemented_whatever_the_branch

#### Scenario: The prefixed-branch path still works

- **Given** an open PR on branch `ci/data-gap-163-slug` for issue #163
- **When** the queue builds
- **Then** #163 still has an implementer
- **Test:** tests/test_issue_review.py::test_the_queue_reads_both_labels_as_one_oldest_first_list

#### Scenario: A PR that closes a DIFFERENT issue does not mark this one

- **Given** an open PR whose body closes #174, and an open issue #163 with no PR
- **When** the queue builds
- **Then** #163 is still offered and #174 is not
- **Test:** tests/test_issue_review.py::test_a_closing_pr_marks_its_issue_implemented_whatever_the_branch

### Requirement: The closing PR supplies implementer activity

When a closing PR is the implementer evidence, its `createdAt`/`updatedAt` SHALL feed `last_implementer_activity`, so the reviewer's window arithmetic sees real work.

#### Scenario: Activity comes from the closing PR

- **Given** an open `fix/`-prefixed PR closing #1176 with a known `updatedAt`
- **When** the queue builds
- **Then** the row's `last_implementer_activity` is that PR's newest timestamp
- **Test:** tests/test_issue_review.py::test_a_closing_pr_marks_its_issue_implemented_whatever_the_branch
