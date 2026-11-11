# Tasks

- [x] 1. The tracked change exists (this directory) before any code/data edit
- [x] 2. The split store is corrected: in `data/measurements.json`, `gemma-3-1b` loses the `MLX` 18 t/s pratikg row, `gemma-4-26b-a4b` loses the `llama.cpp` 50.7 t/s PaulGugAI row, and `qwen3.6-35b-a3b` loses the `llama.cpp` 51.8 t/s xfxjapan row; each figure stays on its owner row; the copied `engagement.seen_posts` entry is dropped from each model in the `data/models.json` catalog. Via `load_store()`/`flatten_store()` every reader sees the corrected flat view (`engines[]` spliced with posts.json counters)
- [x] 3. `README.md` re-rendered as-of the store's own `generated_utc` so the copied rows disappear from engine rows, backend tables and ranking, consistent with the corrected store
- [x] 4. One corrected snapshot appended so `check_no_value_loss` compares the corrected store against the corrected baseline
- [x] 5. `scripts/validate.py`: `same_post_cross_model_duplicates` / `check_cross_model_attribution` — report-only `data`-stage scan naming every identical `(engine, tps, hardware, source_post)` tuple on two model IDs (same pattern as #459)
- [x] 6. `tests/test_cross_model_attribution.py` (new) locks: the three copies are gone from the store, the README renders no copied row, the remaining same-post cross-model tuples are exactly the documented allow-list, a regression is reported not silent, and the check is wired into the `data` stage
- [x] 7. Gates green: `python3 scripts/validate.py --only data,schema,removal,search,mapping,readme` (the `links` stage needs network), `scripts/run_tests.sh`, `python3 scripts/update_trending.py --render-only --dry-run` exits 0 and diffs clean against committed `README.md`, `make openspec-check` green
- [x] 8. `OPENSPEC.md` regenerated (`make openspec-index`); `openspec-index-check` and `check_openspec_tasks` green
