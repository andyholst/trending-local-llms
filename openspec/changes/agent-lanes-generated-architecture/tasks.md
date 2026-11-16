## Tasks — #935: the generated inventory names the agent lanes

- [x] `scripts/architecture_bot.py`: per-pipeline agent-lanes line — each `hermes -z` leg (through wrapper targets, parsed by `scripts/check_agent_skills.py`'s single parser) with its `-s` preload set
- [x] `scripts/architecture_bot.py`: the pipeline's announced marker verbs read from `scripts/bot_markers.py`'s REGISTRY (rule 6j — never re-spelled)
- [x] `scripts/architecture_bot.py`: Agent skill contracts inventory — every `agents/skills/*/SKILL.md`, labeled with its preloading legs or `no leg — orphan contract`
- [x] `scripts/architecture_check.py::findings`: refuse an unnamed skill contract and an unnamed leg preload (`#935` findings, fails `make architecture-check`)
- [x] `tests/test_architecture_bot.py::test_agent_lanes_skill_contracts_and_bot_verbs_are_named` planted-tree proof (preload line, registry verbs, orphan label, regenerated tree re-checks green)
- [x] `tests/test_architecture.py::test_agent_skill_contracts_and_leg_preloads_must_be_named` checker-side red→green proof (fixture gained `hermes_legs` / `skills` planters)
- [x] Regenerate `ARCHITECTURE.md` §10 (`make architecture-refresh`) so the shipped tree is current through the new gates
- [x] `AGENTS.md` §8 guard row for the new checks (rule 3c — attended run; reviewer signs off on the AGENTS.md diff)
