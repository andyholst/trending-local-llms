# Proposal: issue-body-prefile-architect-1814

Issue: #1814
PR: #1816

## Why

Issue #1730 wired `make issue-message-check BODY_FILE=<draft>` into the reviewer, tester and planner filing prompts, but not into `tll-architect`. The architect filed #1808 with `<!-- message-pattern-opt-in -->` and only four of the five sections, so `pr-closure.yml`'s `issues:opened/edited` branch refused the body on run 46002825059. The regression is in the producer path, not the gate: the gate already has the one validator the lanes must call.

## What Changes

- Extend `agents/tll-architect/skills/tll-architect/SKILL.md`'s **File** rule to compose all five sections in order, run `make issue-message-check BODY_FILE=<draft>`, and call `gh issue create` only on a zero verdict.
- Add the architect prompt to `FILING_LANE_PROMPTS` in `tests/test_pr_message.py`, extending the existing #1730 wiring guard rather than adding a second test or a second validator.
- Record the analysis in `findings/1814.md` and archive this tracked change onto the PR head.

## Impact

No new script, Makefile target, workflow, contract, image or `AGENTS.md` row: the same `make issue-message-check` seam is named by one more filing lane and pinned by the guard that already exists for the other three. The guard goes RED on the base revision (2 failing checks) and GREEN on this head.

## Not covered

- No edit to an already-filed issue body by automation (#1808 stays in its owning lane's hands), no CI dispatch, no merge, no push to `master`, no collaborator grant, and no change to the protected `AGENTS.md` rulebook (rule 3c).
