# Tasks

- [x] 1. Proposal + `rulebook-invalid-change-repair` capability spec (three scenarios, each with
      its locking test).
- [x] 2. `AGENTS.md` §2 (rule 6q): land row 1 of #1087 verbatim after the architecture-repair
      paragraph — the incomplete-active-change shape, the `invalid-change-repair` job, its
      `DRIFT=none|index-drift|invalid-change` verdict and `REPAIR=none|archived` half, the
      keeper-PR shape, the no-fabrication half, the registry naming all three repairers.
- [x] 3. `AGENTS.md` §8: land row 2 of #1087 verbatim as a guard-table row beside the
      `test_openspec_binding.py` row, guard name exactly
      `tests/test_openspec_invalid_change_repair.py`.
- [x] 4. `tests/test_agents_rows.py`: `test_the_invalid_change_repair_rows_are_written` pins the
      §6q phrases, the §8 row's seam/targets/contract halves, and that both named modules exist;
      registered in `main()`.
- [x] 5. Proof on the branch: `make owed-rows-check` reports BOTH rows `LANDED` with
      `AGENTS.md:<line>` evidence and `problems=0`; `make lint` and `make openspec-check` green;
      `python3 tests/test_agents_rows.py` and `python3 tests/test_owed_rows.py` green.
- [x] 6. PR with the five-section message pattern closing #1087; full suite green in CI;
      `make openspec-record-pr` archives this change at the PR head.
