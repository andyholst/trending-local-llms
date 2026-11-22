## ADDED Requirements

### Requirement: An open PR that closes an issue is an implementer on any branch

The implementer queue SHALL treat an issue as having an implementer when an OPEN pull request's body binds a closing keyword to that issue, regardless of the pull request's `headRefName`. The prefixed `ci/data-gap-<n>-*` branch signal SHALL remain in force. The decision SHALL use the repository's ONE closing-keyword parser (`scripts/pr_closure.py`), including its rule that a keyword inside a code quote is prose.

#### Scenario: A fix/-prefixed closing PR removes an issue from the queue

- **Given** an open PR on `fix/pr-block-grace-derived-1176` whose body says `closes #1176`
- **When** the implementer queue is built
- **Then** issue 1176 is not offered as `next-sweep` and carries an implementer
- **Test:** tests/test_issue_queue_predicate.py::test_a_fix_prefixed_closing_pr_is_an_implementer

#### Scenario: A PR without a closing binding stays claimable

- **Given** an open PR whose body merely discusses an issue without a closing keyword
- **When** the implementer queue is built
- **Then** the issue stays in the queue with `has_implementer=0`
- **Test:** tests/test_issue_queue_predicate.py::test_a_pr_without_a_closing_binding_stays_in_the_queue

#### Scenario: The one closure parser decides, including code quotes

- **Given** bodies with `closes`, `Fixes`, a different issue number, a code-quoted keyword and no body
- **When** the closing-PR predicate is evaluated
- **Then** only genuine closing bindings to the named issue match
- **Test:** tests/test_issue_queue_predicate.py::test_the_one_closure_parser_is_used_not_a_hand_rolled_regex
