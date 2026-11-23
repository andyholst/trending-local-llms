# Tasks: land-host-ahead-skill-notes-1462

- [x] Cut the worktree from fetched `origin/master` `bd2cc85d` in its own worktree
- [x] Classify all four divergences against the base blob before editing (forward vs stale)
- [x] Land the planner and implementer notes as a lossless union — every master line kept, zero new duplicate bullets
- [x] Land the pure-forward reviewer and pr-rebase notes byte-identical to the host copies
- [x] Add and register `tests/test_fleet_lifecycle.py::test_second_batch_host_ahead_notes_are_landed`
- [x] Run the focused lifecycle module and `make lint` green
- [x] Regenerate `OPENSPEC.md` and keep all OpenSpec gates green
- [x] Run the focused lifecycle module, `make lint`, `make architecture-check`, `make findings-check` and `make pr-message-check` (full suite is CI-only)
- [x] Commit with the agent identity, push the head with a lease, open the ready-for-review PR closing #1462
- [x] Report the final head SHA on issue #1462 and on the PR
