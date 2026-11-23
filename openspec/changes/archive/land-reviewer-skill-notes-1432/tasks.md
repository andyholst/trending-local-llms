# Tasks: land-reviewer-skill-notes-1432

- [x] Cut `rule/reviewer-skill-notes-1432` from the fetched `origin/master` in its own worktree
- [x] Merge the OpenSpec-lifecycle note (`8b`) into the reviewer skill's numbered review list, keeping the offline reproduction command and the #866 reference
- [x] Extend the hand-rolled-test-hygiene pitfall with the double-listed-`test_*` direction and its `test_workflows.py` reference
- [x] Add `test_reviewer_skill_carries_landed_host_ahead_notes` to `tests/test_fleet_lifecycle.py` and wire it into the module's `main()`
- [x] Leave every `agents/*/config.yaml` and `SOUL.md` untouched (#1401 / earlier rules own those)
- [x] Run the focused test module, `make lint`, `make architecture-check` and the OpenSpec gates
