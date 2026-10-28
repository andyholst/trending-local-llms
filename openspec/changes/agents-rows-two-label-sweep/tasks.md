# Tasks

- [ ] 1. Write the proposal + capability spec (`rulebook`) for the owed rows (issues #494 / #497).
- [ ] 2. `AGENTS.md` §6j: the implementer's sweep reads `data-gap-analysis` AND `tech-debt` as ONE oldest-first queue, one issue per run; the reviewer keeps its own default (issue #494).
- [ ] 3. `AGENTS.md` §6e: the `triage.md` verdict (`implement` / `refine` / `close`) taken against the fetched base, `make issue-verdict`, and the REFUSAL of an `EVIDENCE:` block that names nothing in the tree (issue #494).
- [ ] 4. `AGENTS.md` §6b: `issue-bot.yml`'s second schedule slot `49 * * * *` beside `19 * * * *`, the dropped-cron reason, and the serialising `concurrency` (issue #497).
- [ ] 5. `AGENTS.md` §8: rows for `tests/test_issue_triage.py::test_three_mock_issues_decide_implement_refine_or_close_against_the_tree`, `tests/test_issue_review.py::test_the_queue_reads_both_labels_as_one_oldest_first_list` and `tests/test_sweep_alarm.py` (+ `make sweep-alarm`).
- [ ] 6. `tests/test_agents_rows.py`: `test_the_rows_for_the_two_label_queue_and_the_sweep_alarm_are_written` (presence + the module named + the measured failure), registered in `main()`, and `test_the_rows_name_modules_that_exist` extended to prove the evidence gate it cites exists — shown RED on the pre-change `AGENTS.md`.
- [ ] 7. Verified: `make lint`, `make test` (incl. `tests/test_agents_rows.py`, `tests/test_rule_numbers.py`, `tests/test_architecture.py`), `make openspec-check`.
- [ ] 8. `findings.md` written (`make findings-check`); `OPENSPEC.md` regenerated (`make openspec-index`).
