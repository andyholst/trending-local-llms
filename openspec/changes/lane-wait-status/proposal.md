# Proposal: lane-wait-status

Issue: #1232
PR: (pending)

## Why

The TLL fleet runs the same lanes on several machines. A `working on #N`
comment alone does not tell the other host whether a lane is busy, waiting on a
test/CI gate, or free to take the next issue. Two machines then either duplicate
work or go idle while a gate runs. The issue thread is the ONE shared board
(rule §7b), so the waiting state belongs there.

## What Changes

- AGENTS.md §7b gains the while-you-wait status rule: a signed, host-stamped
  comment naming `user@hostname` (e.g. `asimov@omarchy`), what the lane is
  doing, what it is waiting for, and which issue/PR it can help with next —
  posted before work, repeated while a test or CI gate runs and at handover.
- All seven `agents/tll-*/SOUL.md` and the planner skill carry the same rule.
- `tests/test_fleet_handover_protocol.py` asserts the rule and the host stamp
  in all eight files; green on this branch (`ok`) and RED on `origin/master`
  (15 dropped needles).
- AGENTS.md §8 gains the guard row; rule 3c note records the review-required
  section change, declared on the issue before implementation.

## Impact

- Rulebook and lane instructions only. No new make target, script, workflow,
  schedule or credential: `make test` already runs the guard on PR and master
  push.
- The claim, PR comment and signed `done #<id> · handover <...>` shapes are
  unchanged; a status note is an addition, not a replacement.

## Not Covered

- No auto-posting from a bot pipeline: the rule governs the agents' comments.
- No change to the host/repo divergence seam or to the PR/issue closure checks.
