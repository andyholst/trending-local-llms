# Tasks

- [x] 1. `scripts/issue_queue.py` computes the pick order and each candidate's implementer window, and `issue-bot`'s `pick` job reads it through `make issue-queue` (one implementation, rule 6d)
- [x] 2. `issue-bot.yml` announces the window on both paths: one start comment (`<!-- issue-bot-start: … -->`, branch + run, default token) posted BEFORE `make implement-issue`
- [x] 3. `REVIEW_GAP_HOURS := 3` is one Makefile constant, passed to every queue/review call
- [x] 4. `scripts/issue_review.py` provides `--pick`, `--mark`, `--guard`, `--body-hash`, `--check-markers`, `--finish`, and imports `issue_queue` for the window (never a second copy)
- [x] 5. The reviewer defers an issue inside the window (a run in flight, implementer activity younger than the gap, or within the next 3 sweeps) and replies ONCE when an implementer has started; a deferral writes nothing
- [x] 6. The marker carries this run's id, so a run never blocks its own guard re-check while another run's marker still defers it
- [x] 7. `.github/workflows/issue-review-bot.yml` has the trigger surface (hourly `41`, owner dispatch, NO `issues` trigger), the guard, the pick, the two paths, the one-reply rule, the body-unchanged proof and the findings filing — never a push, a branch or a merge
- [x] 8. `Makefile` wires every script and prompt to a target, and `_test` runs the new test file
- [x] 9. `tests/test_issue_review.py` + the `tests/test_workflows.py` cases lock the queue rule, the 3 h boundary (injected clock), the pick/guard/marker behaviour and the wiring — and fail on the pre-change tree
- [x] 10. `AGENTS.md` §6b/§2 6e/6g/§8, `ARCHITECTURE.md`, `README.md` and the `OPENSPEC.md` row describe it
- [x] 11. `make test`, `make architecture-check`, `make openspec-check`, `make validate` and `make secret-scan` are green
