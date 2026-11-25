# Tasks: filer-skip-cancelled-push-runs

- [x] Add the superseded-cancelled-push predicate to `scripts/pipeline_failure_issue.py` and skip such runs in the sweep's master/schedule collection
- [x] Announce the skip count (live and `--dry`), never silent
- [x] Add `test_a_cancelled_push_run_is_not_filed` and prove it RED on `git show origin/master:scripts/pipeline_failure_issue.py` (347 passed / 5 named FAILs on base; 352 / 0 on this head)
- [x] Add `test_a_cancelled_push_run_with_a_readable_diagnosis_still_files` (the #1615 counterexample) and `test_the_superseded_skip_is_announced_in_dry_output`
- [~] Extend the `AGENTS.md` §8 row for `tests/test_pipeline_failure_issue.py` so it names the new guards — blocked: rule 3c human sign-off (AGENTS.md protected in a headless leg); recorded as an owed-row finding
- [x] Update the module docstring / `BAD_CONCLUSIONS` comment and regenerate `ARCHITECTURE.md` §10 (`make architecture-refresh`; the inventory block is unchanged — `architecture-check` green)
- [x] Write `findings/1669.md`, run `make lint` (rc 0), `make architecture-check` (rc 0), `make findings-check ISSUE=1669` (OK) and the focused test module (352 passed / 0 failed)
- [x] Archive the change with `make openspec-archive NAME=filer-skip-cancelled-push-runs` and regenerate `OPENSPEC.md` (archived as `2026-11-24-filer-skip-cancelled-push-runs`; index 1 active / 536 archived)
- [x] Push `fix/filer-skip-cancelled-push-1669`, open READY PR #1673 carrying `Closes #1669`, record `PR: #1673` and hand over to `tll-reviewer`
