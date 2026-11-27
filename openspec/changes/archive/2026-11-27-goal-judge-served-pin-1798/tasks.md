# Tasks: goal-judge-served-pin-1798

- [x] `agents/model_chain.json` declares `auxiliary.goal_judge` by alias, plus a Nous fallback alias list — verified by the new chain suite
- [x] `scripts/agent_model_chain.py` renders the block and refuses a misrouted judge (`auxiliary_problems`) — verified by the new chain suite
- [x] `auxiliary` is an owned block in `agent_model_chain.py` and `agent_profile_provision.py` — verified by the extended provision suite
- [x] The eight `agents/tll-*/config.yaml` files are regenerated from the chain — verified by `make agent-profile-model-render` + `make agent-model-chain-check`
- [x] New guards are RED on the pre-change script (`origin/master`: 6 FAIL) and green on this change (148/0) — measured
- [x] Generated artifacts regenerated (`ARCHITECTURE.md` §10, `OPENSPEC.md`) after the script docstring changes
- [x] `make lint`, `make architecture-check`, `make openspec-check` green; `findings/1798.md` written
- [x] PR opened with the five-section body and `closes #1798`; change recorded/archived on the branch
