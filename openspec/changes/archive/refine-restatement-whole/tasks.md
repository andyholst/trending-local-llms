# Tasks

- [x] 1. Write the proposal + `issue-bot-verdict` capability spec for issue #450.
- [x] 2. `scripts/issue_verdict.py`: `restatement()` joins continuation lines up to the next key line or a blank line.
- [x] 3. `scripts/issue_verdict.py`: `_ends_mid_sentence()` refuses a cut value before any write, naming the tail.
- [x] 4. `tests/test_issue_triage.py`: wrapped → posted whole; truncated → refused with nothing posted; a short complete one still passes.
- [x] 5. Verified RED against `origin/master`'s `issue_verdict.py` (4 failures) and GREEN after (115 passed).
- [x] 6. `AGENTS.md` §8 guard row (rule 6c, review-required rule 3c); `findings.md` written.
- [x] 7. `OPENSPEC.md` regenerated; `make lint`, `make test`, `make openspec-check`, `make architecture-check`, `make findings-check` green.
