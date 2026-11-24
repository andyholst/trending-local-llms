# Proposal: land-forward-skill-notes-1559

Issue: #1559

## Why

At base `674bb36b82d0`, `make fleet-host-sync-check BASE=origin/master` is red on two host-ahead divergences: one additive bullet in the planner `SKILL.md` and two in the reviewer `SKILL.md`. Both have zero deletions against the base blob and neither exists on master, so they are legitimate forward experience, not staleness. They were reported as owed across several wake-ups but had no tracker, leaving the sync gate permanently red and tempting a later M:-sync to overwrite genuine host notes.

## What Changes

- Land the planner RESUME bullet verbatim into `agents/tll-planner/skills/tll-planner/SKILL.md`.
- Land the reviewer read-only-dispatch and Docker-unset-env bullets verbatim into `agents/tll-reviewer/skills/tll-reviewer/SKILL.md`.
- Add `test_fourth_batch_host_ahead_notes_are_landed` to `tests/test_fleet_lifecycle.py`, pinning each needle present exactly once, and register it in that module's `main()`.
- Regenerate `OPENSPEC.md` on the PR head.

## Impact

Documentation-only additive change to two lane skills plus one test guard. No data format, contract, Makefile target, script, pipeline job or image changes. No AGENTS.md rule changes (rule 3c). Host copies stay byte-identical through the landing, which is what lets `fleet-host-sync-check` go green without a wipe.

## Not covered

- No CI dispatch, merge, master push, collaborator grant or owner ruling.
- No other host-ahead notes (only the three measured at this base).
- No fix to the sync gate's inability to distinguish forward work from drift (that is a separate concern).
