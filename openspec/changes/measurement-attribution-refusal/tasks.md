# Tasks

- [x] 1. The tracked change exists (this directory) before any code edit
- [x] 2. `scripts/update_trending.py`: one identity parser (`measurement_model_identity`),
      one mention scanner (`named_models_in_text`) and one reason
      (`misattributed_measurement_reason`) — the same-family/different-size proof, with the
      comparison-cue, own-model, cross-family, unparseable and `MEASUREMENT_MODEL_ALIASES`
      carve-outs
- [x] 3. `refuse_misattributed_measurements` is called in `ingest_raw_snapshots` where a
      raw row merges, loudly refusing the measurement and naming its source post
- [x] 4. `check_post_signal` FAILS a placeholder `source_post` that claims engagement counts
      and keeps a placeholder with no counts a warning (`fabricated_post_signal_reason`, one
      implementation shared with ingest-side use)
- [x] 5. `check_measurement_attribution` is a report-only scan registered in the `data` stage
      CI runs, naming the shipped `qwen-3.6-27b` row without reding history
- [x] 6. `tests/test_measurement_attribution.py` (new) locks the refusal, every carve-out and
      the report-only scan; `tests/test_post_signal.py` locks the placeholder+counts failure
      and the allowed carve-out
- [x] 7. Gates green: `make test`, `make validate`, `make validate-mapped`, `make lint`,
      `make openspec-check`; `OPENSPEC.md` regenerated (run as their python equivalents in
      this agent container — docker is absent: `scripts/run_tests.sh`, `scripts/validate.py
      --only data,schema,mapping,removal,readme` (the `links` stage needs network),
      `scripts/lint_*` via `make lint`, `scripts/openspec_index.py --check`)
