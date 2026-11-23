# Tasks: land-planner-implementer-skill-notes-1440

- [x] Cut `fix/host-ahead-planner-implementer-skills-1440` from the fetched `origin/master` in its own worktree
- [x] Add the three planner host-ahead pitfall notes additively, keeping the existing concurrency bullet and its #1416 reference verbatim
- [x] Add the two implementer host-ahead pitfall notes additively, keeping their #866/#1434 and #972 references
- [x] Extend `test_lane_skill_mirrors_carry_landed_host_ahead_notes` with the five new phrase/reference pairs (test already wired into `main()`)
- [x] Leave every `agents/*/config.yaml` and `SOUL.md` untouched (#1401 / earlier rules own those)
- [x] Run the focused test module, `make lint`, `make architecture-check` and the OpenSpec gates
