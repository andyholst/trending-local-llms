# pr-message-preflight Specification

## Purpose
TBD - created by archiving change live-pr-body-preflight-1710. Update Purpose after archive.

## Requirements

### Requirement: A lane can preflight the live PR body before claiming or handing over a branch

`scripts/pr_body.py` SHALL accept `--check-live-pr <n>` and `make pr-message-check` SHALL accept
`PR=<n>`, reading the named pull request's `body` and `headRefName` through ONE `gh pr view
--json body,headRefName` call and validating them through the SAME `_problems_for` parser the
webhook gate uses. A conforming body SHALL exit 0; a body the message-pattern or closure gate
refuses SHALL exit 1 naming the problem; a failed or unreadable gh read SHALL exit 2 with the
gh error text, never a clean verdict. No workflow, schedule or model call is involved.

#### Scenario: A conforming live body passes with one recorded read

- **Given** an open PR whose live body has the five `##` sections in order and closes the issue its head branch implements
- **When** a lane runs `make pr-message-check PR=<n>` before claiming or handing over that branch
- **Then** the command exits 0, prints the gate's OK line, and the stubbed gh log records exactly one `gh pr view <n> --json body,headRefName` call — no second message-pattern view, no invented field
- **Test:** tests/test_pr_message.py::test_the_live_pr_preflight_refuses_a_body_the_check_rejects

#### Scenario: A body the gate refuses is refused before handover

- **Given** a live PR body that omits one of the five required sections
- **When** the same make target reads that PR
- **Then** it exits 1, prints `REFUSED` on stderr and names the missing section, so the lane can refuse to claim or hand over the branch instead of learning at CI
- **Test:** tests/test_pr_message.py::test_the_live_pr_preflight_refuses_a_body_the_check_rejects

#### Scenario: An unreadable PR is loud

- **Given** `gh pr view` fails (or answers unparseable JSON)
- **When** the preflight runs
- **Then** it exits 2 and prints `cannot read PR #<n>` (or the unreadable-answer error) with gh's own text, changing nothing and never reporting a pass
- **Test:** tests/test_pr_message.py::test_the_live_pr_preflight_refuses_a_body_the_check_rejects

#### Scenario: The seam is reachable through the Makefile, not only the script

- **Given** the real Makefile and a stub `gh` on PATH
- **When** `make pr-message-check PR=<n>` is invoked for a good body and then a bad body
- **Then** the good body exits 0 with a recorded live-PR read and the bad body exits non-zero with the refusal — the pre-push path uses the same make target CI already calls
- **Test:** tests/test_pr_message.py::test_the_live_pr_preflight_refuses_a_body_the_check_rejects
