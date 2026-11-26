# Tasks: parallel-planner-dispatch

- [x] Add the `Parallel implementer dispatch (owner directive, issue #1767)` contract to `agents/tll-planner/skills/tll-planner/SKILL.md` (up to 3 concurrent lanes, DISTINCT open issues, shared-file serialisation via `make dispatch-check ... CLAIMS=`)
- [x] State the five per-lane clauses: own query file, own signed claim/race guard, own worktree, own lease-checked branch, own board-visible bookend pair
- [x] Forbid dispatch onto tech-debt or protected-rulebook work without owner sign-off; restate no tree write, no merge, no master push
- [x] Add `tests/test_parallel_planner_dispatch.py` with a RED-on-base (`git show 37c6d88150fdb...`) and GREEN-on-head source guard, wired into `main()` and discovered by `scripts/run_tests.sh`
- [x] Run the focused guard (5 passed / 0 failed), `tests/test_fleet_lifecycle.py` and `tests/test_planner_orchestration_authority.py` (all green)
- [x] Declare the rule-3c owed rows in `findings/1767-planner.md`: AGENTS.md §8 guard row (registered Owed-row marker) and the protected planner SOUL mirror denied by the harness
- [x] Regenerate `OPENSPEC.md` from the active change and green the OpenSpec checks (proposal, Given/When/Then spec with resolving `Test:` lines, every task ticked)
- [x] Run `make lint`, the PR-message/closure checks and the commit-authorship check; commit as `Andy Holst <andy.holst@protonmail.com>` and push the lease-checked branch
- [x] Open a READY PR linking `Refs #1767` (issue stays open), verify CI registered >0 jobs at the pushed head
