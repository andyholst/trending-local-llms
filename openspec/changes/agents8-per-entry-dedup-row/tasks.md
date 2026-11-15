# Tasks: agents8-per-entry-dedup-row

- [x] AGENTS.md §8 carries the row #996 owed, naming the three landed guards and issues #996/#1001, and containing the ledger needle `tests/test_data_gap_analysis.py --` verbatim (verified: the row exists in §8 and `tests/test_agents_rows.py` passes green against it)
- [x] `tests/test_agents_rows.py` pins the row (`test_the_per_entry_dedup_row_is_written`, wired into `main()` so `make test` runs it) and the suite passes (verified: `python3 tests/test_agents_rows.py` green on this branch)
- [x] `make owed-rows-check` reports #1001's row LANDED with its `AGENTS.md:<line>` evidence (verified on this branch; re-verified on master after merge by the queued-alarm sweep)
