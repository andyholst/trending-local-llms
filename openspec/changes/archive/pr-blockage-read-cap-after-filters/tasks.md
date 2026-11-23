# Tasks: pr-blockage-read-cap-after-filters

- [x] Add `pr_block_candidates()` to `scripts/pipeline_failure_issue.py`: concluded-bad + open-PR branch + inside the window, in that order, before any bounding
- [x] Call it from `pr_triggered_failures` and bound only the candidate list; keep `bound_pr_block_runs()` and its newest-`cap`/skipped-count contract unchanged
- [x] Compute `open_branches(repo)` once in `record_pr_blockages` and pass it into the collection pass
- [x] Extend `tests/test_pipeline_failure_issue.py`: the green-runs-crowd-out guard (RED on `origin/master`), the once-only open-PR read, and move the source-shape needle to the new call site
- [x] Prove the new guard RED against `git show origin/master:scripts/pipeline_failure_issue.py`, then green on this head — 8 FAIL on the base revision (`PASSED 241 | FAILED 8`), `PASSED 250 | FAILED 0` here
- [x] Run the focused modules (`tests/test_pipeline_failure_issue.py`, `tests/test_pipeline_failure_guard.py`) green on the branch head
- [x] Record the owed §8 row as a finding (`findings.md` + `- **Owed-row:**`), never by editing protected `AGENTS.md` (rule 3c) — `make findings-check` rc=0, 1 well-formed finding
- [x] Regenerate `OPENSPEC.md`; run `make lint`, `make validate-search`, `make validate-mapped` — all rc=0 on this head
- [x] Full suite on the branch head: `166 module(s) passed, 1 FAILED` where the one red is THIS change's unticked task box (the change-tasks bootstrap), no code regression
- [x] Re-run the full suite after the last code edit so the change-tasks module is green too
