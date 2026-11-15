# Tasks — agents-skills-relocation-904 (issue #904)

## Relocation (.hermes → agents/skills)

- [x] `git mv .hermes/skills/<name>` → `agents/skills/<name>` for all five leg skills (data-search, bot-unattended, issue-implement, issue-review, pr-fix), content byte-faithful (git shows five `R` renames)
- [x] Remove `.hermes/` entirely (including `.hermes/pr-body-662.md`, a stale scratch file of the retired home with no reader in the tree) and add `agents/skills/README.md` naming the folder as the one home of the leg contracts
- [x] Makefile: `HERMES_SKILLS_DIR := $(CURDIR)/agents/skills` + the `_setup` / search-leg comments that name `.hermes/skills` (five sites)
- [x] `scripts/hermes_skills_register.py`: docstring/help text names agents/skills

## Gate (the #904 scan)

- [x] `scripts/bot_markers.py` gains `canonical_examples()` AND `marker_acceptance()` — each registered marker rendered exactly as the registry itself writes it, and the acceptance patterns derived from the same grammar `parse_markers` reads (ONE definition, rule 6j)
- [x] `scripts/check_agent_skills.py` gains `marker_findings`: scans `agents/skills/*/SKILL.md`, the fleet mirrors `agents/*/SOUL.md` and `agents/*/skills/*/SKILL.md`; a `<!-- <registered-name>` occurrence that is not the registry's own rendering is a finding naming file:line; prose/backtick mentions stay legal; wired into `check()`
- [x] `scripts/check_makefile_knobs.py` reader globs follow the home (`agents/skills/**/*.md`)
- [x] `tests/test_agent_skills.py`: every fixture re-pointed at `agents/skills` (13 test modules rewired), plus `test_registered_markers_in_skills_are_checked_against_the_registry_itself` (re-spelled marker RED end-to-end through `check()`; every canonical rendering GREEN; prose GREEN; shipped tree GREEN) and `test_registration_points_at_agents_skills_and_nothing_lives_in_dot_hermes`

## Text rewiring

- [x] `issue-bot.yml` + `issue-review-bot.yml`: the rc=3 hint and the skills-check error string name `agents/skills`
- [x] `AGENTS.md` §6p names `agents/skills/<name>/SKILL.md` as the skill home (rule 3c — reviewer signs off on this diff; the exact changed lines are declared on issue #904)
- [x] `ARCHITECTURE.md` prose rows that name `.hermes/skills` name `agents/skills`; generated inventory block regenerated (`make architecture-refresh`, 186 lines)
- [x] the remaining test modules that read `.hermes/skills/...` paths read `agents/skills/...`

## Verification

- [x] the new marker scan run against the PRE-change `check_agent_skills.py` (`git show origin/master:scripts/check_agent_skills.py`) stays GREEN on the planted re-spelled owed-row marker (defect reproduced), while the new gate reds it naming `agents/skills/issue-implement/SKILL.md:77` — the guard is new (rule 6c)
- [x] `make check-agent-skills` green (`[agent-skills] ok`), `make lint` green (11 workflows guard-scanned)
- [x] `make test` fully green on the shipped tree (re-run after this file is fully ticked)
