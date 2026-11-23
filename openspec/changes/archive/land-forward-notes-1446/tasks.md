# Tasks: land-forward-notes-1446

- [x] Cut `fix/land-forward-notes-1445` from the fetched `origin/master` in its own worktree
- [x] File #1446 and claim it on its own thread before touching the branch
- [x] Add the two planner host-ahead pitfall notes additively, byte-identical to the host, preserving every existing master byte
- [x] Add the two implementer host-ahead pitfall notes additively, byte-identical to the host
- [x] Extend `test_lane_skill_mirrors_carry_landed_host_ahead_notes` with the four new phrase/reference pairs (test already wired into `main()`)
- [x] Land three further host-ahead notes additively on the master-move rebase: planner cron/no-truncating-filter and do-not-wipe-during-sync; implementer reset-after-regenerate staleness (test pairs added, `main()` unchanged)
- [x] Record the real PR #1448 (the first body closed #1446 on branch suffix `…-1445`, so #1447 was closed and reopened as #1448); regenerate `OPENSPEC.md` on the rebased head
- [x] Leave every `agents/*/config.yaml` and `SOUL.md` untouched (rule-3c protected)
- [x] Run the focused test module, `make lint`, `make architecture-check` and the OpenSpec gates
- [x] Record PR #1448 and archive this change — done by `make openspec-record-pr` after `gh pr create`
