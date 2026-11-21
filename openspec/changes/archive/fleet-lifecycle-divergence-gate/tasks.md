# Tasks

- [x] 1. The tracked change exists (this directory) before any code or rulebook edit
- [x] 2. All seven lane `SOUL.md` files and the planner skill carry the comment-before-work,
      PR-opened and reviewer handover shapes, and the planner reads the newest comment to
      delegate
- [x] 3. `AGENTS.md` §7b added the tll-fleet behaviour section and §8 gained one guard row
      (rule 3c review-required, declared on issue #1209 before implementation)
- [x] 4. `scripts/fleet_host_sync_check.py` + `make fleet-host-sync-check`: compares host
      profiles with `git show <fetched base>` (never the working tree) and the rulebook
      markers; refuses a stale base / missing profile / divergence, naming lane and file
- [x] 5. `tests/test_fleet_lifecycle.py` drives the REAL seam over a scratch home, proves
      green on a synced tree and RED on a planted byte-loss and a bad base, and locks the
      lane/rulebook shapes, the planner's read-before-dispatch rule and the CI wiring
- [x] 6. `ARCHITECTURE.md` target + script rows and regenerated §10; `findings.md` records
      the `.deleted` dot-directory finding; `make lint`, `make architecture-check` and
      `make architecture-refresh` verified
- [x] 7. The gate is wired into `qa-validate`'s `validate` job (both PR and push paths run
      `make test` / `make lint` and the new `make fleet-host-sync-check` step), and
      `make openspec-index` + `make openspec-check` are green on the exact head
