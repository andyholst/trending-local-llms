# pr-closure-guard

## ADDED Requirements

### Requirement: The issue-bot's PR body is checked as a CLAIM, not a marker word

The suite MUST run the issue-bot "Open the PR" step, take the body file it passes to
`gh pr create`, and check it with `scripts/pr_closure.py`: the body closes exactly the
issue the branch implements, with one closing keyword binding one reference.

#### Scenario: the real step's body is checked by the real parser

- **Given** the issue-bot PR step executed with a stub `gh`, for issue 376
- **When** its `--body-file` content is parsed by `pr_closure.check(body, branch)`
- **Then** no problems are reported and the bindings are exactly `[(376, [376])]`
- **Test:** tests/test_workflows.py::test_issue_bot_pr_body_actually_closes_the_issue

### Requirement: The closure assertion refuses the shapes that actually broke

The same assertion MUST fail on a chained closing reference and on a body that closes a
different issue, so it cannot be satisfied by containing the words "closes #".

#### Scenario: a chained reference is refused

- **Given** a body containing `closes #271 and #276` for a branch implementing 376
- **When** the closure parser reads it
- **Then** it reports the extra reference (only #271 would bind) and/or the missing #376
- **Test:** tests/test_workflows.py::test_issue_bot_pr_body_actually_closes_the_issue

#### Scenario: the wrong issue is refused

- **Given** a body containing `closes #999` for a branch implementing 376
- **When** the closure parser reads it
- **Then** it reports that the implemented issue is not closed
- **Test:** tests/test_workflows.py::test_issue_bot_pr_body_actually_closes_the_issue
