# Tasks

- [x] 1. Proposal + capability spec for `pr-fix-names-the-openspec-gate` (issue #560).
- [x] 2. `.hermes/skills/pr-fix/SKILL.md`: a section naming each OpenSpec failure and its remedy, and
  the general rule that the check's own output is the instruction.
- [x] 3. `tests/test_agent_skills.py::test_the_fixer_skill_names_the_openspec_failures` pins the text
  (5 checks, registered in the module's `main()`).
- [x] 4. Regression proved RED on the pre-change skill (the five checks fail without the section).
- [x] 5. `OPENSPEC.md` index refreshed (`make openspec-index`).
- [x] 6. Gates green: `make lint`, `make openspec-check`, `make architecture-check`, `make test`'s
  agent-skills module.
- [x] 7. Commit, push, open the PR (closes #560) — reviewable, never a draft.
