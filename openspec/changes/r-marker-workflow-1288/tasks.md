# Tasks: r-marker-workflow-1288

- [x] Add an additive colon-safe workflow-name token to the `R:` marker in `scripts/watch_monitor.py`
- [x] Add `test_r_marker_carries_workflow_name` guard in `tests/test_watch_monitor.py` (guard/closure vs qa-validate distinct, token cannot inject a colon, nameless run unchanged)
- [x] Run the targeted guard and `make lint` on the worktree, confirm RED on the pre-change monitor
- [ ] Land the first unique commit early
- [x] Write `findings.md` and prove it with `make findings-check`
- [ ] Regenerate `OPENSPEC.md` and run `make openspec-check`
- [ ] Open PR with the five-section message pattern closing #1288; hand to tll-reviewer
