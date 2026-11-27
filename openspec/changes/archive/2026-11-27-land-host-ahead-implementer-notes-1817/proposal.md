# Proposal: land-host-ahead-implementer-notes-1817

Issue: #1817

## Why

`make fleet-host-sync-check BASE=origin/master` reds on `tll-implementer/skills/tll-implementer/SKILL.md` because the host file carries two hard-won operational pitfalls that the checked-in mirror does not: GitHub's branch-rename REST endpoint does not carry an open PR (deleting the old head closes it), and a dispatch that rebinds an existing PR to a different issue than its branch suffix is unsatisfiable without a scope ruling. The previous overlapping front (PR #1813) merged at `774c12d0`, so this file group is free.

## What Changes

- Insert the two pitfall paragraphs into `agents/tll-implementer/skills/tll-implementer/SKILL.md`, byte-for-byte from the host file, before `## Procedure`.
- Extend the existing guard `tests/test_parallel_implementer_lanes.py` with one test asserting both pitfalls are present, so the notes cannot be silently dropped.
- Add this tracked change bound to `Issue: #1817`, archive it on the landing branch and regenerate `OPENSPEC.md`.

## Impact

Skill prose and one test only. No Makefile target, workflow, schedule, credential, data store, generated inventory or rulebook rule changes. Host bytes are left intact; the host already carries the merged #1767 base section alongside these notes (backup `SKILL.md.bak-20261127T140954Z`).

## Not covered

- No merge, master push, CI dispatch or access grant.
- No change to the planner / reviewer skills or to `AGENTS.md`.
