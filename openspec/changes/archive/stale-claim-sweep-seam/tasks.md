# Tasks: stale-claim-sweep-seam

- [x] Add `scripts/stale_claim_sweep.py` — pure decision (`sweep_thread`/`sweep_threads`, `Thread`/`Comment`/`Verdict`) + thin `gh` layer, writing nothing
- [x] Add `make stale-claim-sweep` (live, read-only) and `CHECK=1` (offline contract)
- [x] Wire the offline contract into `qa-validate` beside `make watch-monitor CHECK=1` and register it in `master_alarm.GATES`
- [x] Add `tests/test_stale_claim_sweep.py` driving the REAL pure function (silent under/over threshold, run-bearing, human, terminal, second-tick dedup, unreadable thread exit 2)
- [x] Add the host-side exception entry so the bare `python3` recipe is documented on both sides
- [x] Update `ARCHITECTURE.md` §3 target row + §6 script row and regenerate the inventory block
- [x] Run the targeted module, `make lint` and `make architecture-check`
- [x] Regenerate `OPENSPEC.md` and keep the change bound to `Issue: #1610`
