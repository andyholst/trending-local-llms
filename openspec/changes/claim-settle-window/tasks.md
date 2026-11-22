# Tasks: claim-settle-window

- [x] Name the minimum claim settle window in `AGENTS.md` §7b, pinned to one seam
- [x] Add `CLAIM_SETTLE_SECONDS` to `scripts/watch_monitor.py` and make `--check` refuse a weak floor
- [x] Add the RED-first guard in `tests/test_watch_monitor.py`
- [x] Prove the guard RED against the base revision of the rulebook
- [x] Run `make lint`, the module, and `make test`
- [x] Write `findings.md`, regenerate `OPENSPEC.md` and run `make openspec-check`
- [x] Compose the PR body, open the PR, record and archive the change, push and monitor the checks

Evidence:

- **RED on the base tree** (`git show origin/master:AGENTS.md` + `origin/master:scripts/watch_monitor.py`):
  `FAIL §7b names the claim settle window` and `FAIL the rulebook names the ONE seam that carries the number`.
- GREEN after: `PASSED 50 | FAILED 0`, including the real-CLI floor checks
  (`--check --claim-settle-seconds 30` refused, the floor and the pin accepted).
- **The owed row lands**: `make owed-rows-check REPO=andyholst/trending-local-llms` now reads
  `#1312 section=7b needle='a minimum settle window between a wake-up and a claim' LANDED AGENTS.md:2208`
  (was OUTSTANDING), and the ledger moves `landed=2 outstanding=3` → `landed=4 outstanding=2`.
- The floor is a real contract driven through the real CLI — no product symbol is rebound
  (rule 6m), so the guard fails on the pre-change script rather than on a stub.
- `make lint` and `make architecture-check` green; the §10 inventory did not move.
