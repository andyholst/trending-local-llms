# Tasks: engine-min-model-version-not-build (#1025, #1019)

- [x] Refuse a bit-width or throughput unit right after a build version, digit-complete
      (`(?!\d)` on `_BUILD_VERSION`, `bits`/`bpw` lookahead) — verified by
      `tests/test_engine_min_version_ingest.py::test_bits_per_weight_is_not_a_build`
- [x] Add the ONE model-aware claim reader `engine_min_claim` (model-version collisions
      refused, later real phrases still claim) and register it as the
      `engine_min_version` dimension's `claim` — verified by
      `test_a_model_version_collision_never_fills` and
      `test_a_model_version_is_not_an_engine_build_claim`
- [x] Route `update_trending.fill_engine_min_version` through the claim reader (no second
      vocabulary in `update_trending`) — verified by
      `test_the_build_detector_has_one_implementation`
- [x] `dim_claim` as the ONE reader accessor shared by `analyse()` and every re-checking
      consumer (the real-store pin/contradiction guards) — verified green by
      `test_the_real_store_reports_only_figures_it_can_point_at`
- [x] Refuse `disk` after a `<N>GB on ` size and `offload` after `layer(s)` in
      `_STORAGE_TEXT` (#1019) — verified by
      `test_a_layer_offload_or_file_size_is_not_a_storage_requirement`
- [x] OpenSpec: proposal, MODIFIED capability spec (every scenario names its test),
      tasks ledger
- [x] Full host suite green on the branch head (122 modules; the single red
      `test_openspec_index.py` was the pre-regeneration stale index and passes 26/26
      on the committed tree)
