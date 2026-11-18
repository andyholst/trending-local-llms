# Tasks: stamp-fix-pr-in-ledger (#1099)

- [x] Stamp pass in `scripts/pipeline_failure_issue.py`: `issue_close_refs` / `pr_close_view` (closer read through `scripts/pr_closure.py`'s own parser), `diff_guard`, `stamp_merged_fix_prs` — VERIFIED: `python3 tests/test_pipeline_failure_issue.py` PASSED 174 / FAILED 0
- [x] One-annotation issue stamp: `compose_stamp_comment` / `post_stamp_comment` deduped on the registered marker — VERIFIED by the stamp tests' once/never-double shapes
- [x] `pipeline-ledger-stamp` registered in `scripts/bot_markers.py` (`REGISTRY["queued-alarm"]["stamp"]`, shape in `ledger_stamp_marker` / `parse_ledger_stamp_run`) and named in `AGENTS.md` §6j — VERIFIED: `tests/test_bot_markers.py` green in the suite
- [x] Same `make pipeline-failure-issue` target carries the pass (Makefile annotation; no new target) and the stamped ledger lands through the filer's existing ledger-PR path — VERIFIED: `test_the_stamp_rides_the_filer_s_ledger_pr_landing_through_the_makefile`
- [x] Guard-gate pairing: stamped row clears the gate; stamped row whose named guard was deleted goes RED — VERIFIED: `python3 tests/test_pipeline_failure_guard.py` PASSED 137 / FAILED 0 (incl. `test_a_stamped_row_whose_named_guard_no_longer_exists_is_red`)
- [x] `AGENTS.md` §6r + §8 rows updated (attended change under the owner's 2026-11-18 full-permission directive; rule 3c sign-off is this review) — VERIFIED: §8 row pins the stamp-pass tests, pinned by the suite's rulebook checks
- [x] Gates green: `make lint`, `make test`, `make openspec-check`, `make secret-scan`
