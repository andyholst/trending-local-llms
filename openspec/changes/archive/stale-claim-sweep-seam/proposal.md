# Proposal: stale-claim-sweep-seam

Issue: #1610
PR: #1617

## Why

A stale working-claim blocks a shared branch with **no automatic signal**. Measured on 2026-11-24
by `tll-planner`: issue #1563's bot branch sat `DIRTY`/behind 3 for ~80 minutes under a
working-claim that never pushed, and PR #1561 needed three interventions in the same class. Two
hosts currently decide "is this claim stale?" by reading the thread and guessing, so the same
thread can get two different verdicts. `#1265`'s design (section 5, Child 1) isolates the
DECISION in one repo-owned deterministic seam before any writing half exists.

## What Changes

- Add `scripts/stale_claim_sweep.py`: a PURE decision over gh-shaped payloads plus a thin `gh`
  layer. For every OPEN issue whose NEWEST comment is a signed working-claim
  (`BOT <lane> · working on #<id> · …`), it measures `age = now - createdAt` and emits ONE
  `S:<issue>:<claim-id>:<verdict>` line per threshold crossed, newest-last, verdict
  `stale` (90 min) or `released` (180 min).
- A claim whose own text carries a CI run id (`R:<id>`) or a PR number (`PR #<n>`) gets BOTH
  bounds doubled: CI itself consumes wall clock.
- `<claim-id>` is `sha1(author + created_at + issue + body)[:12]` — stable across ticks, no state
  file. Dedup is available to the caller as the pure function's `announced` argument.
- Refusals: a CLOSED thread, a newest comment that is not a signed `working on` claim (a
  `done`/`handover`/`pr`/`reviewing`/`status` line already moved the thread on), a lane that is not
  one of the eight fleet lanes (a human's claim is never stale), or a claim naming a DIFFERENT
  issue than its thread.
- Add `make stale-claim-sweep` (live, read-only) and `make stale-claim-sweep CHECK=1` (offline
  contract), wired into `qa-validate` beside `make watch-monitor CHECK=1`.
- Add `tests/test_stale_claim_sweep.py` driving the REAL pure function against gh-shaped
  payloads (stubbing only the external `gh`), plus the `ARCHITECTURE.md` §3 target row and §6
  script row.

## Impact

No data format, contract, image, workflow trigger or rulebook change: the seam WRITES nothing
(no comment, label, branch or file), so no behaviour changes anywhere. It is report-only and
additive; Children 2–5 of the `#1265` design (pinned constants + refusals as tests, the `S:`
marker in `watch_monitor`, the rule-3c writing half, cross-host parity) land after it.

## Not covered

- No AGENTS.md / §7b / §6w / §6j text: this child changes no behaviour, so it owes no rulebook
  row (rule 3c).
- No PING or RELEASE comment, no state file, no host cron: the writing half is Child 4.
- No new marker in `scripts/bot_markers.py`: `S:` is a detector marker like `C:`/`R:`/`M:`/`H:`,
  which live in `watch_monitor`, not the bot-window registry.
- No CI dispatch, no merge, no `master` push, no collaborator grant, no new Actions schedule.
