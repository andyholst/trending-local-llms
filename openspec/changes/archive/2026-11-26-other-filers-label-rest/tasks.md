# Tasks: other-filers-label-rest

- [x] `scripts/data_gap_analysis.py` applies `data-gap-analysis` via REST `api -X POST …/labels` and keeps the loud post-write refusal — verified by `tests/test_data_gap_analysis.py` (332 passed, 0 failed)
- [x] `scripts/file_findings.py` applies `tech-debt` via REST and keeps the loud post-write refusal — verified by `tests/test_file_findings.py` (94 passed, 0 failed)
- [x] `scripts/issue_review.py` applies `review-in-progress` via REST in `cmd_mark` (`--remove-label` untouched) — verified by `tests/test_issue_review.py` (138 passed, 0 failed)
- [x] `scripts/issue_verdict.py` applies the verdict label via REST and keeps the loud post-write refusal — verified by `tests/test_issue_triage.py` (142 passed, 0 failed)
- [x] Each stub gh models the PAT (GraphQL refused, REST answered) and each module guard asserts no `--add-label` is attempted — RED-proven against `origin/master`'s scripts: 7/3/2/18 failures respectively, 0 after the fix; scripts restored from copies and all four modules re-run green
- [x] Tracked OpenSpec change (proposal, capability spec with per-scenario tests, this checklist) created through `make openspec-new` and bound with a bare `Issue: #1766` line
- [x] `findings/1766.md` written with the analysis and the owed §8 rows
- [~] Extend the existing AGENTS.md §8 rows for the four test modules to name the REST-label guards — blocked: rule 3c human sign-off (AGENTS.md protected in a headless leg); declared as owed rows in `findings/1766.md`
- [x] Regenerate `OPENSPEC.md` (`make openspec-index`) so the change is indexed on the branch head
- [x] PR opened with the five-section body, one `closes #1766` claim, non-draft, and the change archived on the same head
