# Tasks: query-coverage-unnamed-store

- [ ] `prompt_queries()` drops every composed query that names no row of the store (ONE predicate `UT.query_names_model`)
- [ ] Strengthen the wiring assertion: non-empty AND at least one returned query names a real row
- [ ] Add the RED-first regression test `test_an_all_nameless_store_yields_no_vacuous_query` and wire it into `main()`
- [ ] Prove the guard RED on the base revision (`git show origin/master:scripts/query_coverage.py`) and green here
- [ ] Keep `make query-coverage` untouched (exit 1 uncovered / exit 2 `--top 0`) and run the focused module + `make lint`
- [ ] Write `findings/1688.md`, regenerate `OPENSPEC.md`, then record/archive against the PR
