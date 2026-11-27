# Tasks: ghost-run-head-visibility-1797

- [x] Add the `G:<run>:<pr>` marker for a zero-job action_required PR run to `scripts/watch_monitor.py`, reusing `ghost_run_alarm.ghost_verdict`
- [x] Read jobs only for action_required heads, on the caller's explicit gh, with a per-tick cap; an unreadable head contributes no evidence
- [x] Accept `G:` in `--check` without changing the byte shape of `R:` markers or the failure-only filing rule
- [x] Add guards for marker shape, once-only emission, missing evidence and the capped job read
- [x] Run the focused test (`tests/test_watch_monitor.py`) and the ghost-alarm guard
- [~] Extend AGENTS.md §6w/§8 with the G marker and its owner-identity remedy — blocked: rule 3c human sign-off (AGENTS.md protected in a headless lane)
- [x] Create this OpenSpec change bound to #1797 and regenerate OPENSPEC.md
- [x] Write the PR body and push the branch for review
