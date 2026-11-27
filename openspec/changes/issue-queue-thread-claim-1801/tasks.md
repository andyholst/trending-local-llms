# Tasks: issue-queue-thread-claim-1801

- [x] `scripts/issue_queue.py` reuses `dispatch_guard`'s claim parser and skips an issue with a fresh ACTIVE thread claim
- [x] `tests/test_issue_queue_predicate.py` extended with the four behavioural guards + the one-parser pin
- [x] Guards proven RED on the pre-change `issue_queue.py` (21 passed / 3 failed) and GREEN on this change (24/0)
- [x] Generated artifacts checked/regenerated (`make architecture-check` green, `make openspec-index` run)
- [x] `make lint` + targeted module green; `findings/1801.md` written with the owed-row declaration
- [ ] PR opened with the five-section body and `closes #1801`; change recorded/archived on the branch
- [~] §8 guard-row addition naming `tests/test_issue_queue_predicate.py` — blocked: rule 3c human sign-off (AGENTS.md protected in a headless leg)
