# Tasks — cpu-leg-query-vocabulary-audit (issue #858)

- [x] Add `scripts/query_vocab.py`: `LEG_KEYWORDS` — the ONE home of each leg's curated vocabulary — verified: `python3 tests/test_cpu_query_vocabulary.py` half 1 green (Makefile `$(<BACKEND>_KEYWORDS)` indirections resolved to the dict; `smoke_search` and the CPU fetch sampling import it)
- [x] `Makefile`: `SEARCH_<BACKEND>_QUERIES` become indirections to the home (+ `QUERY_VOCAB_RUN`), prompts unchanged in shape — verified: the resolved-literal comparison in half 1 is green and goes red on a drifted literal
- [x] Replace the CPU vocabulary with the probe-audited co-occurrence queries (`cpu tokens per second`, `llama.cpp cpu tokens per second`, `raspberry pi tokens per second`, `no gpu tokens per second`) — verified: live probes of the silent AND-query vs the yielding queries on the mirror
- [x] `scripts/smoke_search.py`: `page_yields()` content audit, per-query `yield:` / SILENT labels, the answered-but-silent CPU leg exits 2, each rule's verdict sentence printed only for the rule that fired — verified: `python3 tests/test_cpu_query_vocabulary.py` half 2 + `python3 tests/test_smoke_search.py` green (69)
- [x] `scripts/update_trending.py`: CPU fetch sampling imports the home dict — verified: half 1
- [x] `tests/test_cpu_query_vocabulary.py` locks the spec scenarios (one home; yield gate three ways; audited vocabulary; store evidence; verbatim live posts yield candidates) — verified: 32 passed, 0 failed
- [x] `tests/test_smoke_search.py` fixtures carry real rate/model text so the yield labels are proven — verified: 69 passed, 0 failed
- [x] `.hermes/skills/data-search/SKILL.md` + `skills/gather-data.md` state the vocabulary as owned by `scripts/query_vocab.py` — verified: `make lint` agent-skills check green
- [x] `AGENTS.md`: rule 6o vocabulary-home + yield-gate paragraph; §8 guard row (rule 3c review-required diff) — verified by reviewer sign-off on the AGENTS.md diff
- [x] Add the `scripts/query_vocab.py` row to `ARCHITECTURE.md` §6 and regenerate the §10 block — verified: `make architecture-refresh` wrote 179 lines, `make architecture-check` green
- [x] Regenerate `OPENSPEC.md` with the new change — verified: `make openspec-index` wrote 17 active / 234 archived, `make openspec-index-check` green
- [x] Full gates green on the branch — verified by `make lint`, `make test`, `make openspec-check` running on the branch head (CI and the local re-run both execute them)
