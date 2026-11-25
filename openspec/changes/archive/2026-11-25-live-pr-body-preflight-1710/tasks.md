# Tasks: live-pr-body-preflight-1710

- [x] 1. Proposal + capability spec for `live-pr-body-preflight-1710` (issue #1710), bound by a bare `Issue: #1710` header.
- [x] 2. `scripts/pr_body.py`: `--check-live-pr <n>` reads body + head branch with one `gh pr view --json body,headRefName` call and feeds the SAME `_problems_for` parser; a failed/unreadable read exits 2 loudly.
- [x] 3. `Makefile`: `make pr-message-check` accepts `PR=<n>` and forwards to the live-PR seam; no new target and no workflow change.
- [x] 4. `tests/test_pr_message.py`: stub-gh guard over the real CLI and real make target — good body passes with one recorded read, bad body refused and named, failed read loud, both verdicts through make.
- [x] 5. RED-first: the same module over `git archive origin/master` answers `PASSED 37 | FAILED 7`; on this head `PASSED 44 | FAILED 0`.
- [x] 6. `ARCHITECTURE.md`: the hand-maintained `pr-message-check` and `scripts/pr_body.py` rows name the live-PR input.
- [x] 7. Fast offline gates: `python3 tests/test_pr_message.py`, `make lint`, `make architecture-check`, `make check-secret-output`.
- [x] 8. `findings/1710.md` written; `make findings-check` green; `OPENSPEC.md` regenerated and `make openspec-check` green.
