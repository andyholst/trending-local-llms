# Tasks — classify-nov15-red-ledger-rows

- [x] Raise ledger rows 43716345030, 43716362366, 43718826142, 43725338063 to `fix_pr: 1082`, `guard: "tests/test_openspec_index_repair.py"` — VERIFIED: `git diff data/pipeline_failures.json` shows exactly those `fix_pr`/`guard` line pairs (filer fields `undiagnosed`, `targets`, `created_utc`, `issue_number`, `filed_utc` untouched, rule 3b) and `json.load` parses the raised file (20 rows unchanged in count).
- [x] Raise ledger row 43147240875 to `fix_pr: 922`, `guard: "tests/test_owed_rows.py"` — VERIFIED: same diff shows the pair; `python3 -c "import json,sys; json.load(open('data/pipeline_failures.json'))"` clean.
- [x] Pin the classification in `tests/test_pipeline_failure_guard.py::test_the_nov15_ledger_rows_are_classified_onto_their_landed_guards` (rows name the merged PRs, guards are collected by `make test` via `G.guard_test_exists`, filer fields kept; the five classified rows pass the gate verdict with issues CLOSED; the same rows with `fix_pr`/`guard` nulls restored go RED naming `CLOSED without a fix PR` — the raise is proven necessary against the pre-raise shape) — VERIFIED: `python3 tests/test_pipeline_failure_guard.py` -> `PASSED 132 | FAILED 0` (was 110; the new section printed 22 `ok` lines).
- [x] Register the test in the module's `main()` runner — VERIFIED: `main()` now calls it after `test_run_43110467252_is_raised_onto_the_landed_implement_guard()`; the suite's own wiring checks stay green.
- [x] `findings.md` with the run's real findings (filer quotes passing-module `FAIL:` lines as the error class; no leg stamps `fix_pr` on merge) — VERIFIED: `make findings-check` green.
- [x] `make lint` green (linefeed/agent-skill/pin guards) — VERIFIED: green.
- [x] `make openspec-index` + `make openspec-index-check` green (new change listed in `OPENSPEC.md`) — VERIFIED: green on the branch diff against `origin/master`.
- [x] `make openspec-check` green (proposal + spec with Given/When/Then + Test lines + tasks) — VERIFIED: green.
- [x] `make pipeline-failure-guard-check` green end-to-end on the raised ledger (live issue states) — VERIFIED: green.
- [x] `make check-commit-authorship` green on the branch range — VERIFIED: green.
- [x] `make base-rebase BRANCH=ci/keeper-raise-nov15-red-ledger-rows-1039` onto the fetched tip before push — VERIFIED: green (`base-rebase` exit 0).
