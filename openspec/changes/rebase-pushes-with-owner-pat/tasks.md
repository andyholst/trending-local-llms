# Tasks: rebase-pushes-with-owner-pat

- [x] `scripts/pr_health.py`: `pat_push_url()` helper + `rebase_and_push` pushes through the PAT-rewritten GitHub remote when `GIT_PUSH_PAT` is provided, reading the RAW `config --get remote.origin.url` (insteadOf-proof) — verified by the new suite
- [x] `scripts/auto_merge_rebase.py`: the rebased outcome names the push identity it used — verified by the new suite
- [x] `scripts/ghost_run_alarm.py` (new): `ghost_verdict` DECISION in the script (rule 6d); flags concluded `pull_request` main-pipeline runs with zero jobs, exit 1, exit 2 on unreadable reads — verified by the new suite
- [x] `qa-validate.yml` `auto-merge-rebase` step + `pr-health.yml` rebase-sweep step provide `GIT_PUSH_PAT: secrets.FIXBOT_DISPATCH_TOKEN`; reads keep `github.token` — pinned by `test_ghost_run_and_push_identity_wiring`
- [x] `queued-alarm.yml` calls `make ghost-run-alarm` (rule 6m) with the default token, read-only — pinned by the same wiring test
- [x] `Makefile`: `ghost-run-alarm` public target + internal `_ghost-run-alarm` recipe (rule 6m)
- [x] `tests/test_auto_merge_rebase.py`: PAT-identity fixture (configured-URL + transport alias, stub `gh` as the external-system seam, rule 6m), ghost-shape planting from the measured #1115 runs, wiring pins — 83 passed
- [x] New guard verified RED on the old code: the identity/ghost pins fail against `origin/master`'s `scripts/` + workflows (measured before the wiring landed)
- [x] `AGENTS.md` §6s (push identity) + §6l (ghost sweep) + §8 row updated (rule 3c row signed off in this reviewed PR)
- [x] `ARCHITECTURE.md`: §6 scripts row, alarm target row, queued-alarm job description + `make architecture-refresh` inventory regenerated; `make architecture-check` green
- [x] OpenSpec change (proposal, two capability specs with per-scenario tests, tasks) + `make openspec-index` / `openspec-check` green
- [x] Gates green locally: `make lint`, `make secret-scan`, `test_auto_merge_rebase.py`, `test_pr_health.py`, `test_queued_run_alarm.py`, `test_master_alarm.py`
- [x] PR opened with the five-section body and `closes #1115`; CI monitored to green; change archived at the PR head (`make openspec-record-pr`)
