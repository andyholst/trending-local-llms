# Tasks: land-push-and-verify-rule-1423

- [x] Cut `fix/lane-push-verify-rule-1423` from the freshly fetched `origin/master` in its own worktree
- [x] Land the push-and-verify delivery procedure with the fast-check list and the CI-only gate names in `agents/tll-implementer/skills/tll-implementer/SKILL.md`
- [x] Land the push-and-verify dispatch rule (no pre-push full local gate) in `agents/tll-planner/skills/tll-planner/SKILL.md`
- [x] Add `tests/test_fleet_lifecycle.py::test_lane_skills_carry_the_push_and_verify_rule` and wire it into the module's `main()`
- [x] Leave `AGENTS.md` §7b/§8 untouched (rule 3c owns that half) and every `agents/*/SOUL.md` untouched
- [x] Regenerate `OPENSPEC.md` and keep the OpenSpec checks green (`openspec-index-check`, tasks, spec-test lines, binding, duplicate)
- [x] Run the fast offline checks (targeted module, `make lint`, `pr_body.py --check-body-file`) before pushing; the containerised `validate`/`test`/`live-smoke` stay in CI
