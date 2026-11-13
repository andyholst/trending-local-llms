# issue-bot-tasks-gate

## ADDED Requirements

### Requirement: The implementer refuses to open a PR whose new change leaves a task unticked

The implement job of `issue-bot.yml` MUST run `make openspec-tasks-check` after the agent's
implementation step and before the commit + push / open-the-PR steps, under the same
implement gating as the push step. When any ACTIVE change on the branch still carries an
`- [ ]` box, the step MUST fail the run so NO PR opens, and the run's existing always()
outcome mechanism MUST report the failure on the ISSUE. A refine or close verdict MUST skip
the gate. The check MUST NOT pass vacuously: an explicit `NAME` naming no ACTIVE change
fails, and no `NAME` checks every ACTIVE change.

#### Scenario: the measured shape — a change-only PR with every box unticked

- **Given** an implement run whose agent added an OpenSpec change with every `- [ ]` box
  unticked and nothing else
- **When** the run reaches the gate step before commit + push
- **Then** `make openspec-tasks-check` exits 1, the commit/push/PR-open steps are skipped,
  the run is red, and the always() outcome step comments on the issue with `PR: none opened`
- **Test:** tests/test_workflows.py::test_a_new_change_with_an_unticked_box_never_opens_a_pr

#### Scenario: a refine or close verdict opens no PR and needs no gate

- **Given** an implement run whose triage verdict is `refine` or `close`
- **When** the workflow's steps are read
- **Then** the gate step carries the same `verdict == 'implement'` condition the commit step
  carries, so a verdict run never trips it
- **Test:** tests/test_workflows.py::test_the_tasks_gate_runs_only_for_implement_verdicts

#### Scenario: an explicit NAME cannot pass by matching nothing

- **Given** an ACTIVE changes tree that does not contain a change named `ghost-change`
- **When** `check_openspec_tasks.check_all(only="ghost-change")` runs
- **Then** it returns a failure and names the missing change
- **Test:** tests/test_check_openspec_tasks.py::test_a_name_naming_no_active_change_fails

### Requirement: The implementer's skill states the tick rule the gate enforces

The `issue-implement` skill MUST state that a `tasks.md` box is ticked only when the tree
proves that step verified, and that a step the change cannot itself take is written
`- [~] … — blocked: <who/why>` at creation (rule 6f) — never left `- [ ]` when the PR opens.

#### Scenario: the rule is in the skill the leg preloads

- **Given** the `.hermes/skills/issue-implement/SKILL.md` the implement leg preloads with `-s`
- **When** its OpenSpec section is read
- **Then** it carries the ticked-only-when-verified rule and the `- [~] … — blocked:` shape
- **Test:** tests/test_agent_skills.py::test_the_implement_skill_states_the_tick_rule
