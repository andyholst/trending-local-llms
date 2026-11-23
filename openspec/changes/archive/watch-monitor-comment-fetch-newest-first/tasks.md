# Tasks: watch-monitor-comment-fetch-newest-first

- [x] Add the ONE `COMMENT_QUERY` seam and use it for both comment fetches
- [x] Add the one-time `comments_v2` cursor migration (baseline, no flood)
- [x] Add the three guards driving the real `fetch_payload` with a stub `gh`
- [x] Register each new `test_*` in the module's hand-rolled `main()`
- [x] Prove the guards RED on `origin/master`'s `watch_monitor.py` and green on the branch
- [x] Regenerate `ARCHITECTURE.md` §10 and `OPENSPEC.md`; run `make lint`, `make architecture-check` and `make openspec-check`
- [x] Run the full suite on the branch head
- [x] Write `findings.md`, commit, push and open the PR; report on issue #1360
