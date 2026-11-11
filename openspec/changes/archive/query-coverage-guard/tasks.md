# Tasks

- [x] 1. Write the proposal + spec for the query-coverage rule (issue #264).
- [x] 2. `scripts/update_trending.py`: the ONE implementation — the trending models from the store, a query naming each by its id, `query_names_model()`, and the set the searches use (curated base + derived).
- [x] 3. `scripts/query_coverage.py`: `--queries` (what the prompts append) and the coverage report + guard (exit 1 when a trending model is named by no query).
- [x] 4. `Makefile`: the `query-coverage` target, the four prompts appending `$(MODEL_QUERIES)`, and the guard wired into `_validate-search`.
- [x] 5. `tests/test_query_coverage.py` wired into `make _test`: the derivation, the naming rule, the guard and the wiring, falsified.
- [x] 6. README + `ARCHITECTURE.md` (rule 6h), `AGENTS.md` (rule + section-8 row) and `skills/gather-data.md`.
- [x] 7. Gates green: `make lint`, `make test`, `make architecture-check`, `make openspec-check`, `make validate-search`.
- [x] 8. Commit, push, open the PR (`closes #264`) and monitor it green.
