# Tasks

- [x] 1. Proposal + `rulebook-auto-merge-rebase` capability spec (three scenarios, each with its
      locking test).
- [x] 2. `AGENTS.md` rule 6e: land row 1 of #1088 — `make auto-merge-rebase`
      (`scripts/auto_merge_rebase.py`, issue #1049) named as auto-merge's pre-squash gate:
      behind+clean+bot-owned rebases onto the fetched base, regenerates `OPENSPEC.md` on the
      rebased tree, `rebased=true` skips the squash so CI on the new head lands the merge at the
      validated head; human-owned/conflicting stays report-only.
- [x] 3. `AGENTS.md` §6s: the sweep rebaser bullet states the `OPENSPEC.md` regeneration on the
      rebased tree (issue #1088 — the merge-time index gate never sees a rebased tree with a
      stale index).
- [x] 4. `AGENTS.md` §8: land row 2 of #1088 verbatim as a guard-table row beside the
      `test_pr_health.py` rebaser rows, guard name exactly `tests/test_auto_merge_rebase.py`.
- [x] 5. `tests/test_agents_rows.py`: `test_the_auto_merge_rebase_row_is_written` pins the 6e
      phrases, the §6s regeneration phrase, the §8 row's contract halves, and that
      `scripts/auto_merge_rebase.py` + `tests/test_auto_merge_rebase.py` exist; registered in
      `main()`.
- [x] 6. Proof on the branch: `make owed-rows-check` reports BOTH rows `LANDED` with
      `AGENTS.md:<line>` evidence and `problems=0`; `make lint`, `make openspec-index` +
      `make openspec-check` green; `python3 tests/test_agents_rows.py` green.
- [x] 7. PR with the five-section message pattern closing #1088; full suite green in CI;
      `make openspec-record-pr` archives this change at the PR head.
