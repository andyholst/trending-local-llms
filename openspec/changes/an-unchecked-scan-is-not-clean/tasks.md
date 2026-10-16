# Tasks

- [x] 1. Confirm the premise against production: run 38876843174 shows the runs read SUCCEEDING (no run-count NOTE), so the gap is latent — 1 of the bot's checks would silently stop running if the read were refused.
- [x] 2. `scripts/code_review.py`: `main()` records a coverage gap when a check could not run; the scan names it (`UNCHECKED: …`) and exits non-zero.
- [x] 3. `--static-only` exempt by design (it does not ask for the API checks, which is not the same as asking and being refused).
- [x] 4. Three tests in `tests/test_code_review.py`, registered in `main()`: a refused runs read fails and denies the clean bill; a fully-run scan stays green; `--static-only` exits 0.
- [x] 5. Verified RED on `origin/master`'s `scripts/code_review.py` (3 named failures) and green with the fix (40 checks, 0 failures).
- [x] 6. `findings.md`: `- none` (no NEW gap — the `AGENTS.md` row this touches is already #310, and #231 is already filed).
- [x] 7. `make openspec-check`, `make lint`, `make architecture-check`, `make findings-check` green.
- [x] 8. Commit, push, open the PR (ready for review, never a draft).
