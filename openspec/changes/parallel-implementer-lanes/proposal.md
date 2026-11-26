# Proposal: parallel-implementer-lanes

Issue: #1767 (the implementer-lane mirror; the planner mirror and the AGENTS.md rulebook are separate PRs)
PR: pending

## Why

The owner directed on 2026-11-26 that implementer lanes work in parallel rather than draining the board one issue at a time. The tracked implementer `SOUL.md` and skill still describe a single serial lane, so a second implementer running concurrently has no declared contract for issue ownership, claims, shared files, the lane ceiling, leased pushes or reading its own profile. The documented behaviour must be in the files, not only in a chat note.

## What Changes

- Add a `## Concurrent-lane contract (issue #1767)` section to `agents/tll-implementer/SOUL.md` and to `agents/tll-implementer/skills/tll-implementer/SKILL.md`, declaring: one issue + one worktree + one branch per lane; a signed claim on the issue thread before work; no shared branch or file edits; at most 3 live implementer lanes; a lease-checked push; no master push or manual merge; and every lane loads its own `SOUL.md`/`SKILL.md`.
- Add `tests/test_parallel_implementer_lanes.py`, wired into its own `main()`, which reads the real tracked texts and fails on the pre-contract text for both files (RED base rc=1, GREEN head rc=0).
- Add `findings/1767-implementer.md` which declares the protected `AGENTS.md` §8 guard row owed to the rulebook owner (rule 3c).

## Impact

- Capability: `implementer-lane-concurrency`.
- Text + test only: no Python production seam, Makefile, workflow, schedule, `data/` file or host profile byte is changed.
- The other two file groups in #1767 (planner mirrors, protected rulebook) land in separate PRs; this PR references #1767 with `Refs` and does not close it.

## Not covered

- No planner dispatch behaviour, no `dispatch-check` seam, no `AGENTS.md` edit and no credential change.
