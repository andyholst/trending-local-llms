# Tasks: context-benchmark-points-not-windows (#1017)

- [x] Add the ONE model-aware claim reader `context_tokens_claim` (multi-point sweep
      segments refused, stated windows and lone points kept, decimals never split) and
      register it as the `context_tokens` dimension's `claim` through `dim_claim` —
      verified by
      `tests/test_data_gap_analysis.py::test_a_benchmark_sweep_states_no_context_window`
- [x] Tighten the real-store assertions: `unstructured:context_tokens ==
      {qwen-3.6-27b}` exactly and dflash2 named in `missing:context_tokens` — verified
      green (299/0) by
      `tests/test_data_gap_analysis.py::test_the_real_store_reports_only_figures_it_can_point_at`
- [x] `make test` green end to end — verified by the full suite run
- [x] `AGENTS.md` §8 guard-row naming the new test — verified by the §8 row in this
      branch (rule 6c)
- [x] `make openspec-index` regenerated with this change listed — verified by
      `make openspec-index-check`
