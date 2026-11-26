# Tasks — parallel-implementer-lanes (issue #1767, implementer mirror only)

- [x] `agents/tll-implementer/SOUL.md`: add the `## Concurrent-lane contract (issue #1767)` section with all seven lane obligations
- [x] `agents/tll-implementer/skills/tll-implementer/SKILL.md`: add the same contract, with the skill-specific cross-reference
- [x] `tests/test_parallel_implementer_lanes.py`: RED-first guard reading the real tracked texts, wired into its own `main()`
- [x] Prove RED on the fetched base (`37c6d88150fdb73fd0583a59099aee0b418d7927`) with the new test overlaid (rc=1) and GREEN on the head (rc=0)
- [x] OpenSpec change with proposal, capability spec + `- **Test:**` lines, all tasks ticked; `OPENSPEC.md` regenerated
- [x] `findings/1767-implementer.md`: finding + the rule-3c owed `AGENTS.md` §8 guard-row declaration
- [x] Fast offline checks green; the full containerised `make validate` / `live-smoke` run in CI on the pushed head
