# Tasks: fleet-host-reconcile

- [x] Add `MIRROR_RELS` to `scripts/fleet_host_sync_check.py` and use it in the comparison loop (ONE definition of which TEXT mirrors are compared, rule 6d)
- [x] Land `scripts/fleet_host_reconcile.py`: direction classify (`FORWARD`/`STALE`/`MIXED`), lossless union with duplicate-run collapse, backup-first write, host-home and `DEST=` destinations
- [x] Add `tests/test_fleet_host_reconcile.py` driving the REAL seam over a scratch git repo + scratch profile home (RED-first: the module/target do not exist at the base revision)
- [x] Wire `make fleet-host-reconcile` (+ `_fleet-host-reconcile`) and the read-only `qa-validate` step `BASE=HEAD PROFILES_HOME=agents`
- [x] Document `ARCHITECTURE.md` target + script rows and regenerate the generated inventory block
- [x] Run the new module, `tests/test_fleet_lifecycle.py` and `make architecture-check` after the last edit
- [~] Extend `AGENTS.md` §7b's M:-wake duty with `make fleet-host-reconcile` and §8 with this guard row — blocked: rule 3c human sign-off (AGENTS.md protected in a headless leg)
- [x] Write `findings.md` carrying the owed-row declaration and file it through `make file-findings`
- [x] Regenerate `OPENSPEC.md` and leave `make openspec-check` green
