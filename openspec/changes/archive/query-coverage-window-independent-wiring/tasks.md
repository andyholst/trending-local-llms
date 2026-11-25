# Tasks: query-coverage-window-independent-wiring

- [x] Add the ONE `prompt_queries()` seam in `scripts/query_coverage.py` and route `--queries` through it
- [x] Anchor the wiring assertion on the union: non-empty set, every query reaches the expanded prompt, top-N half asserted when present
- [x] Add the RED-first regression test `test_the_prompt_derivation_survives_an_aged_out_trending_band` and wire it into `main()`
- [x] Keep `make query-coverage` untouched (exit 1 on an uncovered ranked model; `--top 0` refused)
- [x] Write `findings/1678.md` and regenerate `OPENSPEC.md`
- [x] Record the completing PR and archive the change (`make openspec-record-pr ISSUE=1678 PR=1684`)
