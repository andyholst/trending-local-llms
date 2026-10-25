# pr-fix-openspec-gate

## ADDED Requirements

### Requirement: The fixer's skill names the OpenSpec gate's failures

`.hermes/skills/pr-fix/SKILL.md` MUST name each OpenSpec failure a red PR presents — an unticked task
checkbox, a stale `OPENSPEC.md`, a change that does not validate, and `openspec-archive-check` — with
the action each requires, and MUST state that the check's own output is the instruction so the run is
never turned into a question.

#### Scenario: the shipped skill names every OpenSpec failure and its remedy

- **Given** `.hermes/skills/pr-fix/SKILL.md`
- **When** the contract test reads it
- **Then** it names the unchecked checkbox, `make openspec-index`, `openspec validate` and
  `make openspec-archive`
- **And** it carries the rule that a failure is never turned into a question
- **Test:** `tests/test_agent_skills.py::test_the_fixer_skill_names_the_openspec_failures`

#### Scenario: ticking a box is not a way to make a gate green

- **Given** the same skill
- **When** its unticked-checkbox rule is read
- **Then** it says a box is ticked only when its step is genuinely done and verified, and that a step
  which cannot be done is reported in the PR body with the box left unticked
- **Test:** `tests/test_agent_skills.py::test_the_fixer_skill_names_the_openspec_failures`
