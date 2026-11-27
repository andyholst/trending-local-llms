# Tasks: host-ahead-lane-skills-1745

- [x] Fetch `origin/master` and cut the `-1745` worktree from the measured base `7cab5e9350a2369500e945e5c9b99a97807eaeac`
- [x] Copy the three backed-up host skill files verbatim into `agents/tll-<lane>/skills/tll-<lane>/SKILL.md` and verify byte identity with the backups
- [x] Verify the diff contains only the documented host-ahead clauses, the one deliberate CI-only supersession, the relocated implementer paragraphs and the restored `#1115` reference
- [x] Add `test_host_ahead_lane_skill_clauses_are_landed` to `tests/test_fleet_lifecycle.py` and wire it into `main()`; prove 13 RED on the base mirrors and green on the head
- [x] Re-run every existing guard module that reads these skills (planner authority, parallel planner/implementer, dispatch guard, fleet lifecycle, pr-message)
- [x] Write `findings/1745.md` and this OpenSpec change, then regenerate `OPENSPEC.md`
- [x] Run the fast offline checks and push a READY PR with `Closes #1745` in title and body
