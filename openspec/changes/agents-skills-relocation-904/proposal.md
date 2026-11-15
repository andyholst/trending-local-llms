# Bot leg contracts move from .hermes/skills to agents/skills; marker scan covers agent skills

**Issue:** [#904](https://github.com/andyholst/trending-local-llms/issues/904)
**Capability:** `agent-leg-skills`

## Why

`#904` found that the gate which scans every preloaded skill
(`scripts/check_agent_skills.py`) has no marker-literal scan, so a preloaded
skill could teach a re-spelled registered marker shape silently — the exact
drift class rule 6j exists to prevent. The reviewer's ruling on the issue
owner-mandates a relocation at the same time: **`.hermes/` is no longer
valid** — the `agents/` folder (its `SOUL.md` files and its `SKILL.md` files)
is the one home for agent skills, used for building the Hermes agent image and
for the host↔repo sync of the fleet souls/skills. So the fix is not "scan
`.hermes/skills`" but "move the leg contracts into `agents/`, delete
`.hermes/`, and scan the agent skills there."

## What Changes

- **Relocation:** the five bot leg contracts move byte-faithfully from
  `.hermes/skills/<name>/SKILL.md` to `agents/skills/<name>/SKILL.md`
  (`data-search`, `bot-unattended`, `issue-implement`, `issue-review`,
  `pr-fix`). Skill NAMES are unchanged, so no `-s` argument anywhere moves.
- **`.hermes/` is removed** from the tree entirely (including the stray
  `.hermes/pr-body-662.md` leftover).
- **The image seam installs from `agents/skills`:** `HERMES_SKILLS_DIR` in the
  Makefile points at `$(CURDIR)/agents/skills`; `make _hermes-skills-register`
  (already parameterised through `scripts/hermes_skills_register.py`) registers
  that directory in the container's Hermes home, and the image build runs
  `_setup`, so the agents-folder contracts ARE the agent skills the built
  image carries (the reviewer's "new install agent for the hermes image agent
  setup" lands through that one existing seam — no second installer).
- **Marker-literal scan (the #904 gate):** `check_agent_skills.py` gains a scan
  of every `agents/skills/*/SKILL.md` AND every fleet mirror
  (`agents/*/SOUL.md`, `agents/*/skills/*/SKILL.md`) for registered marker
  literals derived from `scripts/bot_markers.py` (the ONE definition). A
  `<!-- <name> …` comment whose name is registered and whose rendering is not
  the registry's own canonical shape fails the gate; naming a marker in prose
  or backticks (no `<!--`) stays legal. Wired through the existing
  `make check-agent-skills` step of `make lint` (rule 6d — no new target).
- **Text rewiring:** the Makefile comments, the two workflow rc=3 error hints
  (`issue-bot.yml`, `issue-review-bot.yml`), `AGENTS.md` §6p (rule 3c — the
  row names where `.hermes/skills` is claimed), and the `ARCHITECTURE.md`
  prose that names `.hermes/skills` all name `agents/skills`.
- **Tests:** the fifteen test modules that read `.hermes/skills/...` paths read
  `agents/skills/...`; `tests/test_agent_skills.py` gains planted-fixture tests
  for the marker scan (RED on the old scan, GREEN on the new one).

## Impact

- `agents/`, `.hermes/` (deleted), `Makefile`, `scripts/check_agent_skills.py`,
  `scripts/hermes_skills_register.py` (docstring), two workflows, `AGENTS.md`
  §6p, `ARCHITECTURE.md`, ~16 test modules.
- Every CI stage that reads a skill path (live-smoke none; `make lint` yes) is
  unaffected because the target names do not change.

## NOT covered

- The host↔repo fleet soul/skills sync stays the documented
  `agents-mirror-sync` practice (host profiles are the source for the
  `agents/<profile>/` mirrors; this change makes the tree the live source for
  the container). No new Makefile sync target is invented here.
- Fleet profile `SOUL.md` contents are not edited — only scanned.
