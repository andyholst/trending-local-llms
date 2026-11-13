# Tasks

- [x] 1. Write the proposal + `issue-review-queue` capability spec for issues #547/#548.
- [x] 2. `scripts/issue_queue.py`: `checked()` (one token, enumerated keys, refuse loudly) and `--pick` (one `key=value` line on stdout, reasoning on stderr).
- [x] 3. `scripts/issue_review.py`: `_print_action` validates `action`/`issue`/`path`/`reason` through the same `checked()`.
- [x] 4. `Makefile`: one public `issue-pick` target wrapping `--pick` (rules 6d/6m).
- [x] 5. `.github/workflows/issue-bot.yml`: the pick step copies the producer's value, keeps a loud numeric refusal, and writes with `printf`.
- [x] 6. `.github/workflows/issue-review-bot.yml`: the pick step takes each value whole and refuses a whitespace-carrying value.
- [x] 7. `tests/test_issue_review.py`: the sweep's shipped step driven by the REAL producer output, the producer-side refusals, and the pre-fix shape refused.
- [x] 8. `tests/test_workflows.py`: the wiring guards follow the new contract (no `sed` of the row in the sweep, no `awk` split in the reviewer, whitespace refused).
- [x] 9. `ARCHITECTURE.md` (rule 6h): the `issue-pick` row + the pick job's description, and the generated §10 block refreshed.
- [x] 10. `AGENTS.md` §8 guard row (rule 6c) — review-required (protected file, rule 3c).
- [x] 11. Verified: `tests/test_issue_review.py`, `tests/test_workflows.py`, `tests/test_issue_triage.py`, `make lint`, `make architecture-check`, `make openspec-check`, `make check-secret-output`, and the RED proof of the new guards against the pre-change tree.
- [x] 12. `findings.md` written (`make findings-check` green); `OPENSPEC.md` regenerated (`make openspec-index`).
