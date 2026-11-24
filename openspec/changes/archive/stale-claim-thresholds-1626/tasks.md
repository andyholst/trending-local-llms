# Tasks: stale-claim-thresholds-1626

- [x] Pin both grace pairs as module constants (SILENT 90/180 min, LIVE-RUN 180/360 min) with per-bound floors
- [x] Add the four `Makefile ?=` overrides and forward them from the `_stale-claim-sweep` recipe
- [x] Name the three authority limits (`AUTHORITY_LIMITS`) and enforce them as first-class predicates (`is_human_claim`, `is_terminal_thread`, `is_run_bearing`)
- [x] Extend `--check` with the floor assertions (pinned constants at/above their floors, overrides below a floor refused)
- [x] Add `tests/test_stale_claim_sweep.py` coverage: the pinned pairs, the floors, the Makefile overrides, and the three refusals at one age
- [x] RED-verify the new guards against `git show origin/master:scripts/stale_claim_sweep.py`
- [x] Run the targeted module, `make lint` and the offline contract
- [x] Update `ARCHITECTURE.md` §3 target row + §6 script row and regenerate the inventory block
- [x] Regenerate `OPENSPEC.md` and keep the change bound to `Issue: #1626`
