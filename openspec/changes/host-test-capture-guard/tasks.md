# Tasks: host-test-capture-guard

- [x] `scripts/run_tests.sh` prints `[test] ok <module>` for every passing module (chatter stays out; first-red contract unchanged) — verified by the new suite
- [x] `TEST_RUN` forwards `-e PYTHONUNBUFFERED=1` explicitly — verified by the new suite
- [x] `test:` target tees the capture, refuses an empty capture loudly, reports the trace count, propagates and announces the suite rc — verified end to end through the real recipe with a PATH stub container
- [x] `tests/test_test_capture_guard.py` green on the new code (21/0) and RED on the pre-change runner/Makefile (ran the same module against `origin/master`'s copies in a sandbox: 13 FAIL)
- [x] AGENTS.md §8 guard row added (rule 3c: the row is part of this branch; reviewer signs off on the AGENTS.md diff)
- [x] OpenSpec change (proposal, spec with per-scenario tests, tasks) + index regenerated
- [ ] Full local gate run green (`make lint`, `make secret-scan`, `make openspec-check`, new suite, real host `make test` proving the tee-guard against a live container)
- [ ] PR opened with the five-section body and `closes #911` (never draft)
