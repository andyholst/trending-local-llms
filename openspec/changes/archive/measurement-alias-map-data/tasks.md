# Tasks

- [x] 1. The tracked change exists (this directory) before any edit.
- [x] 2. `data/model_contract.json` gains the optional `measurement_model_aliases`
  model-key (array of ids, unique, not required); `data/MODEL_CONTRACT.md`
  documents it next to `engine_aliases` (rule 6b: contract change in the same commit).
- [x] 3. `scripts/update_trending.py`: `MEASUREMENT_MODEL_ALIASES` is deleted;
  `misattributed_measurement_reason` resolves aliases from the incoming row's and
  the same-id store row's `measurement_model_aliases`, resolving each counterpart
  through the store as before; refusal text names the data key.
- [x] 4. `scripts/validate.py`: `check_measurement_alias_map` registered in the
  `mapping` stage (with its rule-6d comment); the Makefile `--only` lists already
  select `mapping` — verify the wiring test stays green.
- [x] 5. `tests/test_measurement_attribution.py`: the alias scenario drives the
  DATA key (kept / refused-without-it); new `test_attribution_exceptions_live_in_data_not_code`
  proves the literal is gone from the script.
- [x] 6. `tests/test_validate.py`: the dangling-counterpart refusal and the
  resolvable-alias acceptance run against the real check; fixture helpers unchanged
  (optional key).
- [x] 7. `AGENTS.md` §4 names the row key (next to `engine_aliases`) and §8 gains
  its guard row; the issue carries the rule-3c comment naming these sections.
- [x] 8. `ARCHITECTURE.md` needs no §6 row change (no new target/script/stage; the generated inventory is unchanged — `make architecture-check` green),
  `make lint`, `make validate`, `make openspec-check`/`openspec-index-check`,
  `make test` (container — the live probes need the container Hermes) green on the change tree.
- [x] 9. `findings.md` written (`make findings-check`); `OPENSPEC.md` regenerated.
