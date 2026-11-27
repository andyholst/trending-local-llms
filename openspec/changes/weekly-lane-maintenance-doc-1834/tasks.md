# Tasks: weekly-lane-maintenance-doc-1834

- [x] Add `docs/weekly-lane-maintenance.md` with the five-step runnable checklist, the per-host `make fleet-host-sync-check BASE=origin/master` step and the drift-filing path
- [x] State explicitly that the pass is a planner-run cadence with no Hermes cron and no new GitHub Actions `schedule:`
- [x] Add real guards in `tests/test_weekly_lane_maintenance_doc.py` that read the doc; RED-prove them (6 fails on the first draft), then restore green
- [x] Add the tracked OpenSpec change (proposal binding Issue #1834 + Given/When/Then spec whose `Test:` lines resolve + ticked tasks) and regenerate `OPENSPEC.md`
- [x] Run `make lint` and `make openspec-check` locally; open a READY PR with `Closes #1834` in title and body and hand to `tll-reviewer` on the issue
- [~] Cross-link §6 of `docs/fleet-collaboration.md` to this checklist — blocked: companion PR #1836 merge (that doc is not on base `453597d7`; one writer per shared file, serialized after #1833). Guard is conditional and resolves once it lands.
