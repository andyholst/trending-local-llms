# Tasks

- [x] 1. Confirm the gap (proven twice): PR #713 and #719 auto-merged on green after advisory holds; the `auto-merge` job's `if:` had no label check.
- [x] 2. `.github/workflows/qa-validate.yml` — add `Hold if PR carries the do-not-merge label (#722)` (id `dnm-check`) step before squash-merge: reads labels; if `do-not-merge` present, echo the hold + `hold=true` WITHOUT calling `gh pr merge` (clean exit 0, PR stays OPEN, run green).
- [x] 3. Squash-merge step `if:` mirrors the check (`steps.dnm-check.outputs.hold != 'true'`) so a mid-run label still pries the merge off; a mid-run label is caught, and a non-labeled PR is unchanged (existing squash/delete/PAT behaviour intact).
- [x] 4. `tests/test_workflows.py` — retarget `st = step(am, "merge")` to the step whose run calls `gh pr merge` (the hold step's name also contains "merge"); add do-not-merge wiring assertions to `test_auto_merge`.
- [x] 5. Add `test_auto_merge_holds_a_do_not_merge_labeled_pr` executing the REAL hold step (stub `gh`) for both label states; wire it into `main()`.
- [x] 6. Verify: `python3 tests/test_workflows.py` PASSED 971 | FAILED 0; `make openspec-check` green; `make lint-fix` last; commit authored `Andy Holst <andy.holst@protonmail.com>`; pr_closure binds `fix/merge-gate-do-not-merge-722` to `Closes #722`; title AND body carry `Closes #722`.
