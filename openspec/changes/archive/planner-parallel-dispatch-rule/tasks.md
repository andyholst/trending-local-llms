# Tasks: planner-parallel-dispatch-rule

- [x] Reconcile the owner's parallel-dispatch rule into `agents/tll-planner/skills/tll-planner/SKILL.md` (both the lane bullet and the two concurrency pitfalls)
- [x] Pin the rule, its issue references and the kept protocol rules in `tests/test_fleet_lifecycle.py`; follow the renamed bullet in the #1469 pin
- [x] Write `findings/1644.md`
- [x] Run the focused unit module (`python3 tests/test_fleet_lifecycle.py`) green
- [x] Land the change through the OpenSpec lifecycle (`make openspec-record-pr` on the PR head)
