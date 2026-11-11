# Tasks

- [x] 1. Verify #278's merged fix live (run 38876843174) — the secrets check now runs, and the log contradicts itself on the same refusal.
- [x] 2. `scripts/code_review.py`: `_gh_soft` takes `skips: str | None` and names the real cost of a refusal; `defined_secrets` passes `skips=None`.
- [x] 3. `tests/test_code_review.py`: both directions — a refused secrets read claims no skipped check and says it costs none; a refused run-count read still names the check it skips. Registered in `main()`.
- [x] 4. Verified RED on `origin/master`'s `scripts/code_review.py` (2 named failures) and green with the fix (33 checks, 0 failures).
- [x] 5. `findings.md`: `- none` (no NEW finding — the run-count gap it touches is already #309).
- [x] 6. `make openspec-check`, `make lint`, `make architecture-check`, `make findings-check` green.
- [x] 7. Commit, push, open the PR (ready for review, never a draft).
