# Host Hermes fleet souls and skills

**Issue:** [#682](https://github.com/andyholst/trending-local-llms/issues/682)
**PR:** [#688](https://github.com/andyholst/trending-local-llms/pull/688)

## Why

The five host lanes for this repo live under `~/.hermes/profiles/tll-*`. The repository has no copy of their souls or skills, so a later session cannot see the contract. The lanes are started by the owner on the host. They do not run from a new schedule.

## What Changes

- `agents/tll-planner/`, `agents/tll-architect/`, `agents/tll-security/`, `agents/tll-reviewer/`, and `agents/tll-implementer/`: each lane's `SOUL.md` and `skills/<profile>/SKILL.md`, copied from the host profiles.
- `tests/test_host_fleet_souls.py`: the copy contains no cron expression and tells the lane not to add or edit a schedule.
- No file under `.github/workflows/` changes. Existing schedules stay as they are.

## Impact

A reader of the repo can see what each host lane does. No pipeline, no workflow, and no schedule is added or edited.
