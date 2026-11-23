# Tasks: watch-marker-pr-first-seen

- [x] Add `inject_run_prs` (pure) and `resolve_branch_prs` (network, `PR_RESOLVE_MAX` budget) to `scripts/watch_monitor.py` and wire the resolution into `fetch_payload`
- [x] Keep the marker shape unchanged: a push run and an unresolvable PR run keep the shorter form, a live association is never overwritten
- [x] Add `tests/test_watch_monitor.py::test_r_marker_resolves_a_pr_first_seen_after_the_merge` carrying the measured first-sight `pull_requests: []` shape
- [x] Add `tests/test_watch_monitor.py::test_branch_resolution_is_capped_and_never_guesses` driving the real request through a stub `gh` on PATH
- [x] RED-prove the guard: base `scripts/watch_monitor.py` → module fails (`inject_run_prs` absent, exit 1); restored → 71 passed / 0 FAILED
- [~] Extend the EXISTING `AGENTS.md` §8 row for `tests/test_watch_monitor.py` with the first-seen-post-merge resolution — blocked: rule 3c human sign-off (AGENTS.md protected in a headless leg)
- [x] Update `ARCHITECTURE.md` §6's `scripts/watch_monitor.py` row; regenerate §10
- [x] Regenerate `OPENSPEC.md` and run `make lint`, `make architecture-check`, `make openspec-check` and `make test`
- [x] Write `findings.md` with the owed-row declaration and push the branch for review
