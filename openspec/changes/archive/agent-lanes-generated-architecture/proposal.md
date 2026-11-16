# The generated inventory names the agent lanes: leg preloads, marker verbs, skill contracts (issue #935)

**Issue:** [#935](https://github.com/andyholst/trending-local-llms/issues/935)
PR: #1105
**Capability:** `architecture-inventory`

## Why

`ARCHITECTURE.md` §10 is generated (`make architecture-refresh`) and `make
architecture-check` fails when a target, workflow or script is missing from the
description — but the agent half of the system was invisible to it. Rule 6p
mandates that every `hermes -z` leg preloads its contract from
`agents/skills/<name>/SKILL.md`, and rule 6j mandates that the three bots
coordinate through the marker verbs registered in `scripts/bot_markers.py`.
Neither the `-s` preload sets nor the marker verbs nor the skill list on disk
appeared in the generated block, so a leg could silently drop its `-s` pointer
(it would then run with NO contract and still report success — the exact failure
mode rule 6p was written for) or an orphaned skill contract could rot on disk,
and `architecture-check` would stay green because it never looked at lanes.

## What Changes

- `scripts/architecture_bot.py` renders, per pipeline, an **agent-lanes line**:
  each Makefile leg the pipeline calls and the skills that leg preloads
  (resolved through wrapper targets via `scripts/check_agent_skills.py`'s own
  `legs()` parser — one parser, rule 6d), and the marker verbs the pipeline
  announces, read from `scripts/bot_markers.py`'s REGISTRY (rule 6j's table,
  never re-spelled).
- The generated block gains an **Agent skill contracts** inventory: every
  `agents/skills/*/SKILL.md` on disk, each labeled with the legs that preload
  it — or `no leg — orphan contract` when nothing preloads it.
- `scripts/architecture_check.py::findings` refuses the inverse: a skill
  contract on disk that the description does not name, and a preload name a
  Makefile leg passes to `-s` that the description does not name, both as loud
  `#935` findings.

## Impact

- Capability: `architecture-inventory` (generated block + its checker).
- Code: `scripts/architecture_bot.py`, `scripts/architecture_check.py`.
- Tests: `tests/test_architecture_bot.py`, `tests/test_architecture.py`.
- Docs: the regenerated `ARCHITECTURE.md` §10 block; an `AGENTS.md` §8 guard row
  (rule 3c — attended run, reviewer signs off on the AGENTS.md diff).
- **Not covered:** no new make target (both changed scripts are already wired to
  `architecture-refresh` / `architecture-check`); no change to what a leg DOES —
  only what the description must NAME; `check_agent_skills.py` itself unchanged
  (it is imported as the single lane parser).
