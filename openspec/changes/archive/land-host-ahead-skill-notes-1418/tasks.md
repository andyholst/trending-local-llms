# Tasks: land-host-ahead-skill-notes-1418

- [x] Cut `fix/land-host-ahead-skill-notes-1418` from the fetched `origin/master` `36ca1ff0` in its own worktree
- [x] Merge the four host-ahead planner rules into the planner skill's `## Pitfalls` list, dropping the host timestamp header and machine name, keeping #1416/#712/#1239, #1115, #1401 and #1412/#1413
- [x] Merge the six host-ahead implementer rules into the implementer skill's `## Pitfalls` list, keeping #1239, #1398/#1115 and the `scripts/pr_body.py` / `scripts/master_alarm.py` references
- [x] Add `tests/test_fleet_lifecycle.py::test_lane_skill_mirrors_carry_landed_host_ahead_notes` and wire it into the module's `main()`
- [x] Leave every `agents/*/config.yaml` untouched (#1401 owns that half)
- [x] Regenerate `OPENSPEC.md` and keep the OpenSpec checks green (`openspec-index-check`, tasks, spec-test lines, binding, duplicate)
- [x] Run the focused module, `make lint` and the full test suite
