# Tasks: issue-queue-open-pr-window-1324

- [x] File the finding as issue #1324 and claim it on-thread
- [x] Cut worktree `fix/issue-queue-open-pr-window-1324` from origin/master
- [x] Add the RED-first `_pulls` window regression and register it in `main()`
- [x] Prove the guard RED on the pre-change seam (`PASSED 9 | FAILED 1`)
- [x] Change `_pulls` to request only OPEN PRs
- [x] Run the module GREEN, `make lint`, `make test`
- [x] Write `findings.md`, regenerate `OPENSPEC.md`, `make openspec-check`
- [ ] Compose the PR body, pre-check, open the PR, record/archive the change, report the head SHA

Evidence:

- RED on the base seam: `FAIL: _pulls asks gh only for OPEN PRs the live closing PR was crowded out: [1000, 1001, 1002]` — `PASSED 9 | FAILED 1`, script rc=1.
- GREEN after: `PASSED 10 | FAILED 0`; clean foreground `python3 -m pytest tests/test_issue_queue_predicate.py -q` → `6 passed`.
- The stub is only the external `gh` (rule 6m): it honours `--state`, `--limit` and newest-first ordering; the real `issue_queue._pulls` builds the request and parses the answer.
