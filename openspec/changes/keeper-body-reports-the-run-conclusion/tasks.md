# Tasks: keeper-body-reports-the-run-conclusion

- [x] Create the tracked change before any edit (`proposal.md` + Given/When/Then capability spec + this checklist).
- [x] `scripts/openspec_index_repair.py::compose_pr_body`: add additive keyword-only `run_green`/`index_drift`, word a green-with-drift run honestly, keep the red wording byte-identical; add `--run-green`/`--index-drift` CLI knobs through the existing `make openspec-index-repair-pr-body` seam (rule 6d/6m).
- [x] `.github/workflows/qa-validate.yml`: rename the `index-repair` checkout step to name the tree the run validated (red or drifted-green), leaving the two `failure()`-only sibling step names byte-identical; forward `RUN_GREEN`/`INDEX_DRIFT` from the `validate` output to the body seam.
- [x] `Makefile`: forward `RUN_GREEN=1` / `INDEX_DRIFT=<n>` through the existing `openspec-index-repair-pr-body` recipe, keeping it a pure `$(PYTHON_RUN) python3 scripts/…` command.
- [x] RED-first fixture `tests/test_openspec_index_repair.py::test_the_keeper_body_names_the_green_drift_run_it_repairs`: drive the REAL CLI for green run `4546683307`, assert no false "went red", assert the red path unchanged, and pin the step name; call it from `main()`.
- [x] `tests/test_workflows.py`: pin the conclusion wiring (`RUN_GREEN` from `failure()`, `INDEX_DRIFT` from `needs.validate.outputs.index_drift`) on the real `index-repair` job.
- [x] `ARCHITECTURE.md`: correct the §3 `openspec-index-repair-pr-body` row and §6 `scripts/openspec_index_repair.py` row; regenerate `OPENSPEC.md`.
- [x] No `schedule:` key added or edited (the `refresh-bot` cron stays byte-identical), no `agents/*/SOUL.md`, no `AGENTS.md` §7b/§8 text.
- [x] Fast offline checks green: `tests/test_openspec_index_repair.py` (39 passed), `tests/test_workflows.py` (1447 passed), `make lint`, `make architecture-check`, `make openspec-check`.
- [x] Write `findings/<issue>.md`, open the READY PR with `Closes #1651` in BOTH title and body, archive this change on the branch (`make openspec-record-pr`), and post the `pr #1651 · handover tll-reviewer` comment with the head sha on the issue.
