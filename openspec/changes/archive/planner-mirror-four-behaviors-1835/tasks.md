# Tasks: planner-mirror-four-behaviors-1835

- [x] Fetch `origin/master` and cut the `-1835` worktree from the measured base `3dfaa97b4259b0c9d4bf16d1f9669ecc679d35f7`.
- [x] Add "Fleet scale, autonomous pick-up, weekly lane maintenance" and the "Per-host sync check runs from every LLM host" bullet to `agents/tll-planner/SOUL.md`.
- [x] Add "Fleet scale + autonomous pick-up" and "Per-host sync check" to `agents/tll-planner/skills/tll-planner/SKILL.md`.
- [x] Verify the two mirror diffs are additive only (+28/+19 lines, zero deletions) and that the canonical text matches `docs/fleet-collaboration.md` §3/§5/§6 and `docs/weekly-lane-maintenance.md`.
- [x] Run the mirror guards (`test_fleet_lifecycle.py`) and confirm no non-trivial line or clause grows past the pinned union base.
- [x] Write `findings/1835.md` and this OpenSpec change, then regenerate `OPENSPEC.md`.
- [x] Run the fast offline checks and push a READY PR with `Closes #1835` in title and body.
