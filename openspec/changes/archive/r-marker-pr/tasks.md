# Tasks: r-marker-pr

- [x] Resolve each changed run to its PR number in `scripts/watch_monitor.py`
- [x] Add the RED-first guard in `tests/test_watch_monitor.py`
- [x] Prove the guard RED against the base revision of the monitor
- [x] Run `make lint`, the module, and `make test`
- [x] Write `findings.md`, regenerate `OPENSPEC.md` and run `make openspec-check`
- [x] Compose the PR body, open the PR, record and archive the change, push and monitor the checks

Evidence:

- **Live data confirmed first**: `gh api repos/andyholst/trending-local-llms/actions/runs?per_page=8`
  answers `pull_requests: [{number: 1321}]` + `head_branch` for every PR-triggered run, and an
  empty list for a push — so the field was on hand and unused.
- RED on the base seam (`git show origin/master:scripts/watch_monitor.py`):
  `FAIL a PR run's marker carries its PR number`.
- GREEN after: `PASSED 46 | FAILED 0`, including the push-run shape (no trailing field), a
  non-int PR entry (no malformed field), and the field's position after the workflow token.
- The change is additive: a run with no `pull_requests` emits the byte-identical marker it
  emitted before, so every recorded marker and every reader is unaffected.
- `make lint` and `make architecture-check` green (the §10 inventory regenerated; the block
  is unchanged in size).
