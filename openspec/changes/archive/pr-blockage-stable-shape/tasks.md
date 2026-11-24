# Tasks: pr-blockage-stable-shape

- [x] Anchor `failure_shape` on the failing step region (everything before the FILLER marker) and add `exact_failure_shape` as the second dedup axis in `group_pr_blockages`
- [x] Extend the PR-blockage item with an additive `exact_shape`; keep the ledger keys unchanged (rule 3b)
- [x] Name every blocked OPEN pull request in the filed issue (`compose_body`/`file_issue` optional `branches`)
- [x] Add the RED-first guard in `tests/test_pipeline_failure_issue.py`: two diverging-chatter runs of one defect on two different OPEN branches, RED on the base revision and GREEN at the head
- [x] Prove the guard RED against `origin/master`'s `scripts/pipeline_failure_issue.py` (base `f45bd6c8d26d`) and restore the head afterwards
- [x] Run the focused module, `make lint`, `make architecture-check` and `make test`; regenerate `OPENSPEC.md`
- [x] Write `findings.md`; commit on `fix/pr-blockage-shape-1476`, push, open a non-draft PR carrying `Closes #1476` in title and body
