# Tasks

- [x] 1. Write the proposal + `issue-review-queue` capability spec for issue #202.
- [x] 2. `.github/workflows/issue-bot.yml`: drop the `if: steps.pick.outputs.issue == ''` gate on the verdict-note step, with the reason stated beside it.
- [x] 3. `tests/test_workflows.py`: flip the assertion so the step must NOT be gated on the pick's output (the gate cannot come back).
- [x] 4. `ARCHITECTURE.md`: the `pick` → verdict note row says "on every sweep" (issue #202).
- [x] 5. `AGENTS.md` §8: the existing guard row names the measured gate (review-required, rule 3c).
- [x] 6. Verified: `tests/test_workflows.py` (GREEN after; RED with the gate restored), `tests/test_issue_review.py`, `make lint`, `make architecture-check`, `make openspec-check`, `make findings-check`.
- [x] 7. `findings.md` written; `OPENSPEC.md` regenerated (`make openspec-index`).
