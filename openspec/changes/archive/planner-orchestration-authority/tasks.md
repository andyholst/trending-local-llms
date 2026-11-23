# Tasks: planner-orchestration-authority

- [x] Cut `rule/planner-orchestration-authority-1398` from the freshly fetched `origin/master` `e5e52714` in a worktree, leaving the owner's checkout untouched
- [x] Add the Procedure section "Starting a lane (owner directive 2026-11-23)" to `agents/tll-planner/skills/tll-planner/SKILL.md` — directive, mechanism, guardrails, pitfalls
- [x] Write `tests/test_planner_orchestration_authority.py` reading the REAL skill file (no mocks) and register its tests in `main()`
- [x] RED-prove the guard: with the base revision of the skill swapped in, the module fails; with the change it is green
- [x] Leave `agents/tll-planner/SOUL.md` untouched — a protected agent-instruction file (rule 3c); record the owed section in `findings.md`
- [x] Regenerate `OPENSPEC.md` and run `make openspec-check`, `make lint`, `make architecture-check` and the module on the branch
- [x] Compose the PR body, open the PR (title AND body carry `Closes #1398`), record the PR on the change and push
