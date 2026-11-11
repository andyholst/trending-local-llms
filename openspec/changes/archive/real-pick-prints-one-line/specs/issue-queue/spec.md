# issue-queue

## ADDED Requirements

### Requirement: The real pick prints one value line

`make issue-pick` MUST print exactly one non-empty line to stdout — `issue=<number>` or `issue=`
when nothing is takeable — with all reasoning on stderr, so a caller's `OUT=$(make issue-pick)`
holds the value and not the recipe's echo.

#### Scenario: a takeable issue

- **Given** a repository whose oldest unhandled issue is takeable and a `gh` that answers from
  fixtures
- **When** `make issue-pick` runs
- **Then** stdout is exactly one line, matching `issue=<number>`, and no line is a command echo
- **Test:** tests/test_issue_review.py::test_the_real_issue_pick_prints_exactly_one_line

#### Scenario: the reasoning does not pollute the value

- **Given** the same fixtures
- **When** `make issue-pick` runs
- **Then** `issue-queue`'s explanation appears on stderr only
- **Test:** tests/test_issue_review.py::test_the_real_issue_pick_prints_exactly_one_line
