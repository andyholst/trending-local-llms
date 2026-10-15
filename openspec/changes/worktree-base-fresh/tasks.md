# Tasks

- [x] 1. Write the proposal + capability spec for issue #271 (`worktree-base`: fetch-and-assert, worktree off the fetched tip, resume that fetches first).
- [x] 2. `AGENTS.md` rule **6n** (the working copy every implementation starts from, and the assertion) + its §8 guard row; the rule-3c disclosure comment on the issue names the section.
- [x] 3. `scripts/worktree_base.py` — the ONE implementation: `check` / `new` / `resume`, with the loud fetch failure, the stale-base refusal, the never-re-cut refusal, the worktree-inside-the-repo refusal and the "the caller's checkout is untouched" proof.
- [x] 4. `Makefile`: `base-check`, `worktree-new BRANCH=… [IN_PLACE=1]`, `worktree-resume BRANCH=…` (host targets, the seam CI and a human share).
- [x] 5. `.github/workflows/issue-bot.yml`: `make base-check` after the PAT checkout, and the bare `git checkout "$BRANCH"` replaced by `make worktree-resume` / `make worktree-new`.
- [x] 6. `.github/workflows/refresh-bot.yml`: the same `make base-check` in the `aggregate` job, which also cuts a branch.
- [x] 7. `tests/test_worktree_base.py` (real git repositories): the assertion, the loud fetch failure, the worktree at the fetched tip, the refusals, the untouched-caller proof, the rulebook wording, and the resume that works where a bare checkout fails — wired into `make _test`.
- [x] 8. `tests/test_workflows.py`: the marker-word assertion on the resume path replaced by the real wiring, plus `test_issue_bot_asserts_the_base_it_cuts_from`; the push-step test's stub `make` runs the REAL seam against a real clone.
- [x] 9. `ARCHITECTURE.md` (rule 6h): §8's claim made true, the three targets in §3, the script in §6, the new `issue-bot` / `refresh-bot` steps in §4.
- [x] 10. Verified: `make test` (461 passed / 0 failed), `make lint`, `make architecture-check`, `make openspec-check`, `make validate` green; the new workflow guard shown failing on the pre-change `issue-bot.yml` (6 named checks red, 0 with this change) and the bare `git checkout` shown failing on the resume fixture.
- [x] 11. `findings.md` written (`make findings-check` green); `OPENSPEC.md` regenerated (`make openspec-index`).
