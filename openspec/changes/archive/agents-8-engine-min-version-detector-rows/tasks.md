# Tasks

- [x] 1. Proposal + capability spec for #1128 (`agents-guard-registry`: the §8 row #1020/PR #1127 owed, plus the pin that keeps it honest).
- [x] 2. `AGENTS.md` §8 row naming `tests/test_engine_min_version_ingest.py` — `test_bare_engine_names_beside_throughput_figures_never_claim` + `test_explicit_build_phrases_still_claim` and `tests/test_data_gap_analysis.py` — `test_engine_min_version_candidates_are_engine_names_not_build_claims`, citing #1020 / PR #1127 and stating the throughput-adjacency drift class. Verified: `grep -n "test_bare_engine_names" AGENTS.md` names the row (it named nothing on `origin/master`).
- [x] 3. `tests/test_agents_rows.py::test_the_engine_min_version_bare_engine_name_row_is_written` + its `main()` call: row present, names both modules, cites #1020 and #1127, states the drift class and rule 2, sits beside the #214 row, and each cited guard is a real `def test_…(` in the module the row names. Verified: `python3 tests/test_agents_rows.py` green, and RED on `git show origin/master:AGENTS.md` (the base state #1128 measured).
- [x] 4. Verified the guards the row names are green as shipped: `python3 tests/test_engine_min_version_ingest.py` and `python3 tests/test_data_gap_analysis.py` (no assertion changed — #1020's fix already merged as PR #1127).
- [x] 5. `make openspec-index` (index carries the new change) + `make openspec-check` (change validates, binding green, backlog under the cap).
- [x] 6. `make lint` (rule 6i newlines, workflow guards, agent skills), `make architecture-check` (no target/script/job moved) and `make secret-scan` green.
- [x] 7. `findings.md` written and `make findings-check` green.
