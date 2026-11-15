# agent-leg-skills (delta for agents-skills-relocation-904)

## MODIFIED Requirements

### Requirement: every bot leg preloads its contract from a project skill under agents/skills

Every `hermes -z` bot leg in the `Makefile` preloads its contract with
`-s <skill>,bot-unattended`, and every named skill exists at
`agents/skills/<skill>/SKILL.md` — the `agents/` folder is the ONE home for
agent skills (reviewer ruling on #904: "the .hermes skills are no longer
valid"). `.hermes/` exists nowhere in the tree. `make _hermes-skills-register`
registers `$(CURDIR)/agents/skills` in the container's Hermes home and
`_hermes-skills-check` reads it back, so the built image carries the
agents-folder contracts and `hermes -s` resolves them. The inline prompt stays
a pointer plus this run's parameters within `PROMPT_BUDGET`.

#### Scenario: every leg preloads a skill that exists under agents/skills

- **Given** the shipped tree
- **When** `make check-agent-skills` reads every `hermes -z` recipe and each `-s` name
- **Then** every named skill is present at `agents/skills/<name>/SKILL.md` with matching frontmatter `name`, and `.hermes` is not a tracked path
- **Test:** `tests/test_agent_skills.py::test_the_real_legs_preload_a_real_skill` — real gate on the shipped tree, GREEN

#### Scenario: a leg naming a missing skill is refused

- **Given** a fixture tree whose recipe preloads `no-such-skill`
- **When** the gate runs
- **Then** it exits non-zero naming the recipe and the missing path
- **Test:** `tests/test_agent_skills.py::test_the_gate_fails_each_defect` — real guard on a fixture tree (`a leg naming a skill that does not exist` case), RED

#### Scenario: the container registers agents/skills, not .hermes/skills

- **Given** the shipped `Makefile`
- **When** `make check-agent-skills` asserts the registration seam
- **Then** `HERMES_SKILLS_DIR` points at `$(CURDIR)/agents/skills` and no recipe, workflow or script still names `.hermes/skills`
- **Test:** `tests/test_agent_skills.py::test_registration_points_at_agents_skills_and_nothing_lives_in_dot_hermes` — real gate + tree grep, GREEN

## ADDED Requirements

### Requirement: the skills gate scans agent skills for re-spelled registered markers

`scripts/check_agent_skills.py` (through `make check-agent-skills`, a step of
`make lint`) scans every agent skill file — `agents/skills/*/SKILL.md`, the
fleet mirrors `agents/*/SOUL.md` and `agents/*/skills/*/SKILL.md` — for
registered marker literals derived from `scripts/bot_markers.py` (the ONE
definition, rule 6j). An HTML-comment occurrence `<!-- <name>…` whose name is
registered must render exactly the registry's canonical shape
(`scripts/bot_markers.py::canonical_examples()`); any other rendering of a
registered name fails the gate. Naming a marker in prose or backticks (no
`<!--`) is legal. A NEW marker literal (not a registered name) is left to
`tests/test_bot_markers.py`, which owns the unregistered-literal direction.

#### Scenario: a re-spelled registered marker inside a skill fails the gate

- **Given** a fixture tree whose `agents/skills/issue-implement/SKILL.md` carries `<!-- owed-row: section=<id> needle=<needle> -->` (missing the registry's quotes)
- **When** `check_agent_skills.check` runs
- **Then** it returns a finding naming the file, line and marker name
- **Test:** `tests/test_agent_skills.py::test_registered_markers_in_skills_are_checked_against_the_registry_itself` — real guard on a fixture tree, RED on the old scan (which stayed green on the planted defect — this is #904)

#### Scenario: the registry's own canonical renderings are legal in skills

- **Given** every `canonical_examples()` rendering written into a fixture skill file
- **When** the gate runs
- **Then** it produces no marker findings
- **Test:** `tests/test_agent_skills.py::test_registered_markers_in_skills_are_checked_against_the_registry_itself` — canonical renderings case, GREEN

#### Scenario: the shipped agent skills carry no re-spelled marker

- **Given** the shipped `agents/` tree
- **When** `make check-agent-skills` scans it
- **Then** zero marker findings are produced
- **Test:** `tests/test_agent_skills.py::test_registered_markers_in_skills_are_checked_against_the_registry_itself` — shipped-tree case, GREEN
