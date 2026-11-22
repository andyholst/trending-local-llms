# Proposal: planner-reviewer-board-note

Issue: #1261
PR: #1309

## Why

Producers cycle faster than reviewers, so the open-PR backlog grows while issues are
all "claimed". Measured: 14 PRs open at once, and #1241, #1242, #1247, #1248, #1254,
#1255 and #1257 all waited for a first-review slot while the owner and `asimov@mac`
were active on other threads. The planner's board note tracks which lane works which
ISSUE; nothing names the PRs already awaiting review, so reviewer capacity becomes the
second bottleneck behind the queue.

## What Changes

- `agents/tll-planner/skills/tll-planner/SKILL.md` gains an explicit board duty: the
  planner's board note NAMES the open PRs awaiting a first review and hands each to
  `tll-reviewer` by name, with the PR number, head sha and base.
- The same section states the order: an issue with no PR is dispatched to an
  implementer; an open PR awaiting review is dispatched to `tll-reviewer` FIRST, so
  review capacity is spent before new PRs are produced.

## Impact

Skill text only — no script, target, workflow, data or contract change. The reviewer
keeps its own `data-gap-analysis` default and never touches a `tech-debt` body.

## Not covered

- Any change to the reviewer's queue rule (`scripts/issue_queue.py`) or to the
  `REVIEW_GAP_HOURS` window.
- Adding a reviewer lane or a second reviewer; the issue is explicit that this is a
  dispatch-order fix, not a capacity increase.
