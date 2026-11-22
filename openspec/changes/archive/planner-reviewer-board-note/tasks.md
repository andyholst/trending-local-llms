# Tasks: planner-reviewer-board-note

- [x] Add the reviewer-board duty to `agents/tll-planner/skills/tll-planner/SKILL.md`
- [x] Add the RED-first guard in `tests/test_fleet_handover_protocol.py`
- [x] Prove the guard RED against the base revision of the skill
- [x] Run `make lint`, the module, and `make test`
- [x] Write `findings.md`, regenerate `OPENSPEC.md` and run `make openspec-check`
- [x] Compose the PR body, open the PR, record and archive the change, push and monitor the checks

Evidence:

- RED on the base revision of the skill (`git show origin/master:agents/tll-planner/skills/tll-planner/SKILL.md`):
  `FAIL 2` — the reviewer-board duty and the spend-review-before-producing order are both absent.
- GREEN after: the module ends `ok`; the three needles resolve in the planner skill and no
  earlier needle moved (`test_next_issue_duty_is_documented` still green).
- Skill text only: no `scripts/` module changed, so the §10 inventory block is untouched
  (`make architecture-check` not stale).
