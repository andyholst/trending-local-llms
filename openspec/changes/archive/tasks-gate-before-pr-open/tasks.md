# Tasks: tasks-gate-before-pr-open

- [x] `issue-bot.yml`: gate step `make openspec-tasks-check` after the agent/salvage
      steps and before Commit + push / Open the PR, gated with the push step's
      `verdict == 'implement'` condition — verified by `tests/test_workflows.py`
      (presence, ordering after `make implement-issue` and before `branch-adopt` /
      `gh pr create`, make-only wiring, non-`always()` shape: green 1061/0).
- [x] `tests/test_workflows.py`: `test_a_new_change_with_an_unticked_box_never_opens_a_pr`
      + `test_the_tasks_gate_runs_only_for_implement_verdicts` registered in `main()` —
      both green.
- [x] `tests/test_check_openspec_tasks.py::test_a_name_naming_no_active_change_fails`
      proves a NAME naming no ACTIVE change fails loudly against a planted fixture —
      green (29/0 before this change's own boxes were ticked; suite green after).
- [x] `.hermes/skills/issue-implement/SKILL.md`: tick rule stated (ticked ONLY when the
      tree proves; owed step = `- [~] … — blocked:` at creation; an opened PR never
      carries `- [ ]`) + `tests/test_agent_skills.py::test_the_implement_skill_states_the_tick_rule`
      — green (145/0).
- [x] OpenSpec change shape: `proposal.md` + `specs/issue-bot-tasks-gate/spec.md` (every
      Scenario Given/When/Then with a `- **Test:**` line naming an existing test) —
      `openspec validate` passed it inside `make openspec-check`; only this file's own
      unticked boxes were red there, which this tick fixes.
- [x] Generated artifacts regenerated for the new step: `make architecture-refresh`
      (`[architecture-bot] wrote the inventory block (180 lines)`, and
      `make architecture-check`: `OK the inventory block matches the tree`) and
      `make openspec-index` (`make openspec-index-check`: `OPENSPEC.md is current:
      17 active, 240 archived`).
- [x] `make lint` green (workflow-guard scan: 11 workflows OK; full lint exit 0).
