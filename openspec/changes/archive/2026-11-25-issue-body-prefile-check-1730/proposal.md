# Proposal: issue-body-prefile-check-1730

Issue: #1730
PR: #1740

## Why

`pr-closure.yml` runs `make issue-message-check ISSUE_EVENT=…` on `issues:opened/edited/reopened` for bodies that declare `<!-- message-pattern-opt-in -->`. Run 45597931849 failed in job `closure` on #1727's body: it declared the marker but omitted `## Technical Solution`, so the gate refused a body a bot lane had already filed. The producer side relies on a lane remembering; the validator already has a file seam (`make issue-message-check BODY_FILE=<draft>` → `scripts/pr_body.py --check-issue-file`) that nothing requires the filing lane to use before `gh issue create`.

## What Changes

- Require the filing lanes' prompts (`tll-reviewer`, `tll-tester`, and `tll-planner`) to write a draft issue body to a file, run `make issue-message-check BODY_FILE=<draft>`, and call `gh issue create` only when that verdict is zero.
- Extend `tests/test_pr_message.py` with a guard naming those prompt files and the preserved Makefile/CLI seam, so the requirement cannot be dropped silently.
- Record the protected `AGENTS.md` §8 row as an owed row from this headless leg (rule 3c), not written in this change.

## Impact

No new script, target, workflow, contract or image. The CI gate itself is unchanged; `make issue-message-check` remains the ONE issue-body validator. Filing lanes gain one pre-file step; a declared body that skips a section is refused before it reaches GitHub.

## Not covered

- No change to `AGENTS.md` (protected, rule 3c), no CI dispatch, no merge, no push to master, no collaborator grant, and no editing of an already-filed issue body by automation.
