# Tasks

- [x] 1. This tracked change exists (proposal + capability spec + checklist) before
      any data or test edit
- [x] 2. Verified the implementable scope against the captured posts: 4 genuine,
      post-backed, correctly-typed values isolated from the detector over-matches
      (see triage.md / proposal "Not covered")
- [x] 3. `data/models.json`: `qwen3-8-flash-next-125b` and
      `qwen3-8-flash-next-125b-mtplx-rd1-1` gain `context_tokens: "200000"`
      (additive, rule 3b)
- [x] 4. `data/models.json`: `qwen3.8-27b-ps5lm-native` gains
      `engine_min_version: "llama.cpp port (PS5LM)"` and `qwen3.8-27b-bonsai-2`
      gains `engine_min_version: "PrismML llama.cpp fork"`
- [x] 5. `tests/test_data_gap_analysis.py` gains the `context_tokens` backfill
      traceability + coverage-floor guards (the #163 engine_min_version test now
      auto-covers the two new engine values)
- [x] 6. Regenerated the README (`python3 scripts/update_trending.py`) so card-fit /
      engine cells reflect the four structured values
- [x] 7. `make openspec-index` + `make openspec-index-check` (index row current)
- [x] 8. Gates green on this head: `make lint`, `make test`, `make validate`,
      `make validate-mapped`, `make openspec-check`, `make architecture-check` (or
      the invariant reports confirmed where the container gate cannot run here)
- [x] 9. `findings.md` written; `make findings-check` green
