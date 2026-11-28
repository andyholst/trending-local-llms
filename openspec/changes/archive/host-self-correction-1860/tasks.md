# Tasks: host-self-correction-1860

- [x] Cut a worktree from freshly fetched `origin/master` (base `d0f5dc5840e86db1a331734480397abebb3447ae`) on branch `fix/host-self-correct-1860`
- [x] Define the single comparison set in `scripts/fleet_host_sync_check.py`: `MIRROR_RELS` + `RULEBOOK_REL` + `PROTECTED_RELS`; use the constant in the rulebook marker check
- [x] Extend `scripts/fleet_host_reconcile.py` to compare the single host `AGENTS.md` against the repo-root rulebook with the existing classify / lossless-union / backup-first path; add the repo-tree `--rulebook` override
- [x] Add the attended rule-3c sign-off (`--attended-signoff`, Makefile `ATTESTED=1`) and refuse the whole write set before any backup when a protected file is pending without it
- [x] Keep report-only the default; plumb `ATTESTED` / `RULEBOOK` through the Makefile seam and update the target description
- [x] Wire `qa-validate.yml` to the read-only rulebook comparison (`RULEBOOK=AGENTS.md`); the four new divergence guards run in CI through `make test`, and no CI step passes `WRITE=1`
- [x] Add RED-first guards: STALE converges, FORWARD preserved, protected write fails closed, `config.yaml` untouched, Makefile/CI wiring; run `python3 tests/test_fleet_host_reconcile.py` green
- [x] Add this change dir (proposal + Given/When/Then spec + ticked tasks) and regenerate `OPENSPEC.md`
- [x] Run `make openspec-check`, `make openspec-archive-check`, `make architecture-check`, `make lint` and `make test` green
- [x] Open PR READY with `Closes #1860` in BOTH title and body; `make pr-message-check PR=<n>` before the issue handover
