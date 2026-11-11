# Tasks

- [x] 1. Write the proposal + capability spec for issue #344 (`issue-review-queue`: the `issue=` line carries the number, the shipped parser proves it, a non-numeric `ISSUE=` is refused, a failed thread step stops its consumers).
- [x] 2. `scripts/issue_review.py`: `--pick` prints per-candidate diagnostics as `candidate=<n> position=…`, leaving `issue=` for the action alone.
- [x] 3. `.github/workflows/issue-review-bot.yml`: the pick step takes the first token and refuses a non-numeric `issue=`; the resolve step refuses a non-numeric `ISSUE`; the thread step gets `id: thread` and its consumers are gated on it; the `always()` close is gated on `steps.mark.outcome`.
- [x] 4. `Makefile`: `_review-issue-number` refuses a non-numeric `ISSUE=` on every `review-issue-*` target that takes one.
- [x] 5. `tests/test_issue_review.py`: row assertions on `candidate=`, the real `--pick` output driven through the shipped step, the pre-fix shape refused, and the Makefile refusal.
- [x] 6. `tests/test_workflows.py`: the wiring guards for the thread id, the consumer gating, the close gating and the numeric validation.
- [x] 7. `AGENTS.md` §8 guard row (rule 6c) and `ARCHITECTURE.md` (rule 6h).
- [x] 8. Verified: `make test`-equivalent suite, `make lint`, `make validate`, `make validate-mapped`, `make architecture-check`, `make openspec-check` (what this environment can run).
- [x] 9. `findings.md` written (`make findings-check` green); `OPENSPEC.md` regenerated (`make openspec-index`).
