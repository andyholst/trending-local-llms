# Proposal: fleet-lane-handover-protocol

Issue: #1189 — "fleet: lanes must hand over on the issue thread — a signed done
PR: #1191
comment naming the next lane"

## Why

The fleet's lanes claim work with a signed
`BOT <lane> · working on #<id> · branch … · blocked on … · next …` comment
(issue #703), but nothing makes a lane **hand over**. Measured on the open board:
a lane finishes and the thread stops at "working on" — no done marker, no next
lane, no progress state. The planner and the owner must re-read every thread to
learn who is doing what and who owns the next step. The lane skills say "report
state to the planner", but no `SOUL.md` or skill defines the comment shape, so the
record is inconsistent across lanes and sessions.

## What Changes

- Every `agents/tll-*/SOUL.md` (planner, architect, security, reviewer,
  implementer, tester, pr-rebase) gains a **Handover** section: progress comments
  are the record, a finished lane posts a signed
  `BOT <lane> · done #<id> · handover <next-lane|owner|none> · <next action>`
  comment, and a lane never works outside its remit.
- `agents/tll-planner/skills/tll-planner/SKILL.md` gains the dispatch/handover
  shape (`BOT tll-planner · dispatch #<id> · lane <lane> · base <sha> · done
  <criteria> · handover <next>`) and the standing board rule that the parent
  fleet issue #682 is closed — the board is the issue thread itself.
- `tests/test_fleet_handover_protocol.py` locks the protocol: every lane's
  `SOUL.md` carries the handover shape, the progress-comment rule and the remit
  rule, and the planner skill carries the dispatch/handover shape.

## Impact

- The board becomes followable: each issue thread names the lane working it, the
  done state, and the lane that owns the next step.
- No behaviour change to the product, the data pipeline, the Actions bots or the
  merge gate. The host profiles are re-synced from the repo after this lands
  (a host act recorded on the issue, not a repo test).

## Not covered

- A repo-side seam that copies `SOUL.md` + skills into `~/.hermes/profiles/`
  (the host sync is done by the owner's agent and recorded on #1189).
- Any new lane, cron or GitHub Actions schedule.
- The Actions bots' marker protocol (rule 6j) — untouched.
