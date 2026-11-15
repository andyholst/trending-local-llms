# Tasks

- [x] 1. The tracked OpenSpec change exists (this directory) before the PR, bound to
      `Issue: #1006`, with a proposal, a capability spec and this checklist
- [x] 2. `scripts/data_gap_analysis.py` `_ENGINE_MIN_TEXT` refuses a `<version>`
      immediately followed by a throughput unit (`tokens/s` / `tok/s` / `TPS`) at
      the version token, applied to the engine→version, version→engine and
      adapter/fork branches (the `_BUILD_VERSION` lookahead)
- [x] 3. `tests/test_data_gap_analysis.py` gains
      `test_engine_min_version_detector_refuses_a_throughput_after_the_engine`
      locking each over-match red (`tokens/s`, `tok/s`, `TPS`, both the engine and
      reverse direction via the real rows), the genuine-build-before-a-later-speed
      control green, and the two real rows (`qwen2.5-0.5b`, `gemma-4-e4b`)
      reclassifying to the acquisition bucket
- [x] 4. The real shipped store: `qwen2.5-0.5b` and `gemma-4-e4b` leave
      `unstructured["engine_min_version"]` (7 → 5 models) and no captured text for
      them matches `_ENGINE_MIN_TEXT` (acquisition gap, the correct class)
- [x] 5. Python-side gates verified on the head: `python3 tests/test_data_gap_analysis.py`
      passes (274 ok / 0 failed), and `openspec_index.py --check`, `openspec-binding-check`,
      `openspec-backlog-check`, `check_openspec_tasks`, `check_openspec_test_lines` and
      `openspec_duplicate_check` all pass on this tree (the docker-gated `make openspec-*` CLI
      validation and the full `make test`/`make lint` matrix run on the identical tree in CI —
      docker is not available in this unattended host)
- [x] 6. `OPENSPEC.md` index carries the new change's row (regenerated from the tree)
- [x] 7. `findings.md` at the repo root records the analysis (rule 6g; the sibling
      model-version/bit-width overmatch is a filed finding, never fixed here)
