# Tasks

- [x] 1. The tracked change exists (proposal, capability spec, tasks) before
      any data or test edit, and names its Issue (#991) (rules 6f/952)
- [x] 2. `data/measurements.json`: add `context_tokens: "200K"` (the exact
      figure the shared source post states) to the `MTPLX` measurement on
      `qwen3-8-flash-next-125b` and on `qwen3-8-flash-next-125b-mtplx-rd1-1` —
      additive (rule 3b), contract-declared optional key, correctly attributed
- [x] 3. `tests/test_data_gap_analysis.py` gains
      `test_context_tokens_ingest_traceable_rows_carry_the_post_state`: the two
      MTPLX rows carry the structured `context_tokens` figure, and the real
      `source_post_figure_flags` reports no gated hard-field contradiction on
      them (the readback runs the REAL scan, rule 6m)
- [x] 4. README regenerated from the store; `make validate --only data`
      (source-post readback gate) green; `make lint`, `make test`,
      `make openspec-check` + `make openspec-index` green on the exact head
- [x] 5. `findings.md` written (rule 6g): acquisition/estimate/untraceable
      classes and the rejected `unstructured` candidates recorded as findings
- [~] 6. AGENTS.md §2 gains a hard-rules guard row naming `tests/test_data_gap_analysis.py` (blocked: rule 3c human sign-off; AGENTS.md protected in a headless leg) — the issue's declared `Owed-row`; the full row text is recorded as an `Owed-row` finding so `make file-findings` + `make owed-rows-check` report it OUTSTANDING until an attended run applies it
