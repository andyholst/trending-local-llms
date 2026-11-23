# Tasks: watch-monitor-explicit-gh-client

- [x] Remove the `client = gh_client()` reassignment in `scripts/watch_monitor.py::fetch_payload` so the caller's `client` serves every leg (comments, resolution, master read)
- [x] Add `tests/test_watch_monitor.py::test_fetch_payload_keeps_the_explicit_gh_client` and register it in the module's hand-maintained `main()` (rule 6d)
- [x] Prove the guard RED on the pre-fix seam: sentinel `gh` invoked for `pr list` and `commits/master`; GREEN on the fix (19 passed, no check-parity drift)
- [~] Extend the existing AGENTS.md §8 row for `tests/test_watch_monitor.py` with the one-client contract — blocked: rule 3c human sign-off (AGENTS.md protected in a headless leg)
- [x] Write `findings.md` with the owed-row declaration and file the tracking issue
- [x] Regenerate `OPENSPEC.md` and run `make lint`, `make openspec-check`, `make architecture-check` and the targeted test
