# Tasks: fleet-tll-fleet-profile-model-chain (issue #1140)

- [x] Measure the model chain from the live Portal (`https://inference-api.nousresearch.com/v1/models`,
      2026-11-19: 413 models, exactly 5 at pricing 0) so every id in the chain is a spelling the
      gateway serves — never an invented model name (rule 2)
- [x] `agents/model_chain.json`: `primary` `meituan/longcat-2.5:free`, the four other free models as
      `fallback`s in list order, `deepseek/deepseek-v4-flash-0731` as the single paid `last_resort`,
      `key_env: NOUS_API_KEY` only, each step's measured `context_window`
- [x] `scripts/agent_model_chain.py` — the ONE seam (rule 6d): `write` renders every
      `agents/tll-*/config.yaml` from the chain, `check` refuses a drifted config / a broken chain
      shape / a last resort that is not `$(HERMES_MODEL)` under `$(HERMES_ALIAS)` / a credential
      ASSIGNMENT, `report` prints the order, lanes derived from `agents/tll-*/SOUL.md`
- [x] `Makefile`: `_agent-profile-model-render` + `agent-profile-model-render`,
      `_agent-model-chain-check` + `agent-model-chain-check`, `_agent-model-chain-report` +
      `agent-model-chain-report` (rule 6d), and `agent-model-chain-check` bundled into `make lint`
      so `qa-validate`'s `validate` job and `scripts/fix_loop.sh` both run it (rule 6m)
- [x] `DOCKER_RUN` / `TEST_RUN` forward `NOUS_API_KEY` by NAME (rule 3e) so a lane container is
      never keyless
- [x] Render the seven lane `agents/tll-*/config.yaml` from the chain and verify byte-for-byte
      reproduction from a fresh tree (`make agent-profile-model-render` → `make agent-model-chain-check`)
- [x] `tests/test_agent_model_chain.py` — 10 tests, standalone module, discovered by `make test`
      (chain order, render, hand-edit refusal, chain-shape refusals, pin refusal, credential refusal,
      exit-2 UNDECIDABLE, missing lane, fresh-tree render, wiring) — all green
- [x] `ARCHITECTURE.md`: the three target rows, the `scripts/agent_model_chain.py` §6 row, the
      `lint` row that now bundles the check, and `make architecture-refresh` for the inventory block
      (rule 6h)
- [x] `AGENTS.md` §8 guard row for `tests/test_agent_model_chain.py` (rule 6c; attended run, so the
      rule-3c sign-off is this session's approval — no rulebook rule changed, only the guard table)
- [x] `make openspec-index` — `OPENSPEC.md` current with this change listed
- [x] Gates green locally: `make agent-model-chain-check`, `make lint`, `make architecture-check`,
      `make openspec-check`, `make secret-scan`, `scripts/run_tests.sh`
- [x] PR opened (not draft) with the five-section body and one closing keyword on #1140, the change
      archived at the PR head (`make openspec-record-pr`), then the pipeline monitored to green
      (rule 6e)
