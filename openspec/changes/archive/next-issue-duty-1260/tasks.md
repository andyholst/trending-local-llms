# Tasks: next-issue-duty-1260

- [x] Add `tests/test_fleet_handover_protocol.py::test_next_issue_duty_is_documented` and prove it RED on the base tree (10 FAIL).
- [x] Add the post-delivery duty to all seven `agents/tll-*/SOUL.md` files and to the planner skill.
- [~] Add the §7b bullet and §8 row to AGENTS.md — blocked: rule 3c human sign-off (AGENTS.md protected in a headless leg); exact row in findings.md.
- [x] Regenerate ARCHITECTURE.md and run `make architecture-check`, `make lint` and `make openspec-index` (all 0).
- [x] Run full `make test` and record the result on issue #1260 and the PR (suite rc=2 only on the two OpenSpec gates while this box was unticked; all 147 other modules green; re-run after tick returns rc=0).
