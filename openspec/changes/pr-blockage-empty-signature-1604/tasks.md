# Tasks: pr-blockage-empty-signature-1604

- [x] `scripts/pipeline_failure_issue.py` gains `PR_BLOCK_CONCLUSIONS = ("failure",)` and
  `EMPTY_SHAPE`, and `pr_block_candidates` keeps only `failure` runs — verified: the new unit
  check "only the `failure` run survives the candidate filter" is green
- [x] `group_pr_blockages` skips a member whose `shape` and `exact_shape` are both `EMPTY_SHAPE`
  — verified: the new grouping checks are green (empty signatures file nothing, a real shared
  region still groups)
- [x] `tests/test_pipeline_failure_issue.py` carries the two new tests (unit + end-to-end) —
  verified: `PASSED 337 | FAILED 0`; RED-first against `origin/master`'s script
  `PASSED 332 | FAILED 5`
- [x] OpenSpec change created with proposal, capability spec (per-scenario `**Test:**` lines) and
  this checklist; `OPENSPEC.md` regenerated
- [x] Fast offline gates on the branch: `make lint`, `make openspec-index-check`,
  `python3 scripts/pr_body.py --check-body-file` for the PR body
- [~] The EXISTING `AGENTS.md` §8 row for `tests/test_pipeline_failure_issue.py` is extended to name `test_cancelled_and_empty_signature_runs_never_form_a_pr_blockage` and `test_two_cancelled_open_pr_runs_file_no_pr_blockage_end_to_end` — blocked: rule 3c human sign-off (AGENTS.md protected in a headless leg); declared in `findings/1604.md` as an owed row
