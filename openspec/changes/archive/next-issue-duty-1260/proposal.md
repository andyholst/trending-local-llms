# Change: next-issue-duty-1260

Issue: #1260
PR: #1286

## Why

On 2026-11-22, 14 open issues already carried an open PR while 24 had none. Several lanes
posted `done`/`handover` and then went quiet: §7b described claim, PR, review and handover,
but not what a lane must do after its own delivery. The planner could only dispatch from
comments nobody was obliged to post.

## What Changes

- Add a §7b bullet: after a delivery, a lane re-reads the issue board and signs a claim on
  the oldest unclaimed actionable issue (new worktree), or — when none is unclaimed — files
  an evidence-backed issue and hands it to `tll-planner`.
- Add the same duty to every `tll-*` lane's `SOUL.md` and the planner skill, so the rule is
  read by the lanes that must follow it, not only by the rulebook.
- Add a `tests/test_fleet_handover_protocol.py` guard, extend its §8 row, and prove it RED
  on the base tree.

## Impact

Rulebook + agent prompts + one guard. Rule 3c review-required: the §7b bullet and §8 row
are declared on issue #1260 before implementation.

## Not Covered

No queue re-prioritisation, no automatic dispatch, no new CI schedule, no lane grants.
