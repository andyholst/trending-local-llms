# Tasks: land-forward-notes-1446

- [x] Cut `fix/land-forward-notes-1445` from the fetched `origin/master` in its own worktree
- [x] File #1446 and claim it on its own thread before touching the branch
- [x] Add the two planner host-ahead pitfall notes additively, byte-identical to the host, preserving every existing master byte
- [x] Add the two implementer host-ahead pitfall notes additively, byte-identical to the host
- [x] Extend `test_lane_skill_mirrors_carry_landed_host_ahead_notes` with the four new phrase/reference pairs (test already wired into `main()`)
- [x] Leave every `agents/*/config.yaml` and `SOUL.md` untouched (rule-3c protected)
- [x] Run the focused test module, `make lint`, `make architecture-check` and the OpenSpec gates
- [~] Record PR #1447 and archive this change — blocked: PR not yet opened at task creation; `make openspec-record-pr` will complete it after `gh pr create`
