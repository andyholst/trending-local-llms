# Tasks

- [x] 1. The tracked change exists (this directory) before any agent-file edit
- [x] 2. Every `agents/tll-*/SOUL.md` gains the Handover section: the signed
      `BOT <lane> · done #<id> · handover <next-lane|owner|none> · <next action>`
      shape, the progress-comment rule, the multi-machine shared-board rule, the
      double-claim race guard and the remit rule
- [x] 3. `agents/tll-planner/skills/tll-planner/SKILL.md` gains the
      `BOT tll-planner · dispatch #<id> · lane <lane> · base <sha> · done <criteria>
      · handover <next>` shape, the multi-machine/race-guard rules and the standing
      board rule (parent #682 is closed)
- [x] 4. `tests/test_fleet_handover_protocol.py` locks the protocol over the seven
      SOUL files + the planner skill; RED on the pre-change tree
- [x] 5. Gates green on the exact head: `make lint`, `make test`,
      `make openspec-check`, `make openspec-index` + `openspec-index-check`
- [x] 6. Host profiles re-synced from the repo (`SOUL.md` + skill byte-identical),
      recorded on issue #1190; the PR closes #1189
