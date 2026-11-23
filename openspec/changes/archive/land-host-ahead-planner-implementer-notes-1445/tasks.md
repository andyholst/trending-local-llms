# Tasks: land-host-ahead-planner-implementer-notes-1445

- [x] Cut `fix/host-ahead-planner-implementer-skills-1445` from the fetched `origin/master` in its own worktree
- [x] Land the planner host-ahead notes (dispatch-check concurrency rewrite, protected instruction files, auto-close hidden half), restoring #1239/#712/#1416/#1423
- [x] Land the implementer host-ahead notes (rebase `--amend` message, merge-tree index race), restoring #866/#1434/#972
- [x] Extend `test_lane_skill_mirrors_carry_landed_host_ahead_notes` with the six new phrase/reference pairs (test already wired into `main()`)
- [x] Leave every `agents/*/config.yaml` and `SOUL.md` untouched
- [x] Run the focused test module, `make lint` and the OpenSpec gates
