# Proposal: ghost-pr-handoff-1251

Issue: #1251
PR: #1253

## Why

Measured on 2026-11-22: after `auto-merge-rebase` pushed rebased heads of PRs
#1236, #1237 and #1188, each new qa-validate run completed `action_required`
with ZERO jobs and `gh pr checks` was empty; the actor was
`github-actions[bot]`. Local gates on those exact heads were green. A lane that
reads that as a red gate either loops on code that is fine or waits forever on
a run that never started. The 0-job handoff is a fleet protocol gap, not a
code failure.

## What Changes

- AGENTS.md §7b gains one bullet: recognise the #1115 ghost shape (newest run
  `action_required`, zero jobs, bot actor), post a FAILURE REPORT on the ISSUE
  with run URL and first evidence, re-push ONLY your own branch with an
  owner-git-identity empty commit, and verify with `gh run view <id> --json jobs`
  that jobs actually exist. Another lane's branch is never touched without a
  signed handover.
- AGENTS.md §8 gains one regression row naming this module.
- `tests/test_fleet_handover_protocol.py` pins both needles in AGENTS.md and is
  RED on the base revision.

## Impact

- AGENTS.md §7b and §8 only; no workflow, make target, script or data format
  changes.
- One test module extended; `make fleet-host-sync-check BASE=origin/master`
  still passes because the rulebook markers are additive.

## Not covered

- No change to qa-validate's `auto-merge-rebase` implementation (that is #1115).
- No change to another lane's branch or PR, and no CI dispatch from a bot.
