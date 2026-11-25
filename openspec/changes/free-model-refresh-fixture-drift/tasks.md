# Tasks — free-model-refresh-fixture-drift (issue #1744)

- [x] `tests/test_free_model_refresh.py`: `shipped_free()` / `shipped_alias()` derive ids, contexts and alias from `agents/model_chain.json`; all seed payloads and retirement/no-op/context-drift assertions use them
- [x] `tests/test_agent_model_chain.py`: chain-order string, fallback model list and hand-edit fixture come from the chain instead of five hardcoded ids
- [x] `tests/test_agent_profile_provision.py`: the primary config line and drift fixture come from `AMC.read_chain(root)[0].primary.model` in all four places
- [x] New guard `test_the_fixtures_follow_the_live_chain_not_a_snapshot` wired into `main()`: RED-first — FAIL count 3 on the base test sources, 0 on this head
- [x] Measured on the refreshed keeper head `3b76356492`: all three modules PASSED (97/0, 72/0, 39/0) with the fixed tests overlaid; base `03987d9` also PASSED for all three
- [x] No production code, Makefile, workflow or data-shape change; no other branch retargeted
- [x] `findings/1744.md` filed with the owed §8 row declared (rule 3c attended write)
- [x] `make lint` + fast offline targeted modules green
- [x] OpenSpec change: proposal, capability spec with Test lines, this checklist; index regenerated
- [~] Full `make validate` / `live-smoke` are CI-only — blocked: qa-validate runs them on the pushed head
