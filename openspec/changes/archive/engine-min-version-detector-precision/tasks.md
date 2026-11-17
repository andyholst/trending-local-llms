# Tasks: engine-min-version-detector-precision (#1020)

- [x] Extend `_TPUT_RATE` to every throughput spelling the posts use (`t/s`,
      `tok[en]s?/s`, `…/sec(ond)`, `tokens per second`, `TPS`) so a version followed by
      any rate unit stays refused at the token — verified by
      `tests/test_engine_min_version_ingest.py::test_bare_engine_names_beside_throughput_figures_never_claim`
- [x] Refuse the version→engine adjacency when the rate sits on the ENGINE side
      (`llama.cpp` + `'s <N> <rate>` / `<N> <rate>`, the `345.9 vs llama.cpp's 306.9
      tokens/s` shape) — verified by the same planted test and the real-store reader
      guard `test_engine_min_version_candidates_are_engine_names_not_build_claims`
- [x] Refuse `cuda` glued into a `C++/` or `C/` compound as the engine word (the
      `0.0.3 (C++/CUDA` shape) while `CUDA 12.4` still matches — verified by
      `tests/test_data_gap_analysis.py::test_engine_min_version_candidates_are_engine_names_not_build_claims`
- [x] Real-store readback: the seven #1020 candidates stay out of every
      `engine_min_version` ingest class and the PrismML build sentence still claims —
      verified by `tests/test_data_gap_analysis.py::test_engine_min_version_candidates_are_engine_names_not_build_claims`
- [x] OpenSpec: proposal, MODIFIED capability spec (every scenario names its test),
      tasks ledger
- [~] AGENTS.md §8 guard rows for the two new tests — blocked: rule 3c human sign-off
      (AGENTS.md protected in a headless leg); full row text recorded in findings.md
