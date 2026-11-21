# Tasks

- [x] 1. The tracked change exists (this directory) before any data or test edit
- [x] 2. `data/models.json`: the `qwen3.6-35b-a3b` row gains
      `measurement_model_aliases: ["qwen3.8-27b"]` — additive (rule 3b), counterpart
      is a store model id, contract-declared key
- [x] 3. `tests/test_measurement_attribution.py` gains
      `test_the_shipped_joint_figure_is_documented_as_data` locking: the alias on the
      shipped row, the joint figure clearing the WARN list, the undecided
      `qwen-3.6-27b` hit staying reported, and the shipped alias passing
      `check_measurement_alias_map`
- [x] 4. Gates green on the exact head: `make lint`, `make test`,
      `make validate --only data` (attribution WARN list = the one undecided row),
      `make openspec-check`, `make openspec-index` + `openspec-index-check`
- [x] 5. Issue #650 carries the owner-ruling request (evidence block) for the
      `qwen-3.6-27b` llama.cpp 140 t/s removal; the PR references #650 and closes
      nothing
