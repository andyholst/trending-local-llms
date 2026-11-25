## ADDED Requirements

### Requirement: auto-merge holds a PR whose body fails the message pattern

`qa-validate.yml`'s `auto-merge` job SHALL run `make pr-message-check` against its own
`pull_request` event payload BEFORE any rebase or squash step, and SHALL publish an
allowlisted `hold=true|false` key. A refusal SHALL hold — every later merge-path step
(rebase, head-check, squash-merge, post-squash closure proof) skipped through its `if:` —
leaving the pull request OPEN and the run green (a hold, never a failure). A clean verdict
SHALL leave the merge path exactly as it was.

#### Scenario: A non-conforming body is held, not merged

- **Given** an open, non-draft, same-repo pull request whose body lacks one of the five
  required sections
- **When** `auto-merge` runs after `validate` and `live-smoke` are green
- **Then** the message-pattern step exits 0 having published `hold=true`, the refusal text
  reaches the job log, no `gh pr merge` call is made, and the pull request stays open
- **Test:** tests/test_workflows.py::test_auto_merge_holds_a_non_conforming_body

#### Scenario: A conforming body is still merged

- **Given** the same pull request carrying a body that satisfies `make pr-message-check`
- **When** `auto-merge` runs
- **Then** the step publishes `hold=false` and the squash-merge step's `if:` still admits it,
  so the merge path is unchanged
- **Test:** tests/test_workflows.py::test_auto_merge_holds_a_non_conforming_body

#### Scenario: The hold reaches the product through make

- **Given** the workflow text of `qa-validate.yml`
- **When** the hold step's `run:` block is read
- **Then** it calls `make pr-message-check` with `PR_EVENT` bound to `github.event_path`,
  and writes only the allowlisted `hold=` key to `$GITHUB_OUTPUT`
- **Test:** tests/test_workflows.py::test_auto_merge_holds_a_non_conforming_body

#### Scenario: The hold runs before the squash and gates it

- **Given** the ordered steps of the `auto-merge` job
- **When** the hold step's position is compared with the squash-merge step's
- **Then** the hold precedes it, and the squash-merge `if:` carries
  `steps.message-check.outputs.hold != 'true'`
- **Test:** tests/test_workflows.py::test_auto_merge_holds_a_non_conforming_body
