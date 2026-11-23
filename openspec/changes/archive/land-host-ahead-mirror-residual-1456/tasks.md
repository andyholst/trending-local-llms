# Tasks: land-host-ahead-mirror-residual-1456

- [x] Measured the residual against the fetched base `d4096735`: host-only lines absent from master in `tll-planner` (1 sub-bullet), `tll-implementer` (4 bullets), `tll-reviewer` (7 notes) and `tll-pr-rebase` (5 bullets)
- [x] Confirmed #1468's dedupe (`d609921d`) is already on master, so this change carries NO dedupe
- [x] Landed each host-ahead block once at its host position, keeping master's own text verbatim
- [x] Reconciled the host machine name out of the shared mirrors (no `asimov@mac`, no timestamp header)
- [x] Verified the mirror diff is additive and no duplicate line or double blank was introduced (section list unchanged)
- [x] Kept master's pinned `#1423`/`#1427` text so `tests/test_fleet_lifecycle.py::test_lane_skills_carry_the_push_and_verify_rule` stays green
- [x] Fast offline checks green: `tests/test_fleet_lifecycle.py`, `test_fleet_handover_protocol.py`, `test_host_fleet_souls.py`, `test_planner_orchestration_authority.py`, `test_planner_skill_store_shape.py`, `test_agent_skills.py`, `scripts/lint_linefeeds.py`
- [x] OpenSpec change (proposal, Given/When/Then spec with per-scenario tests, tasks) + index regenerated and the change archived against PR #1465
