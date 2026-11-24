# Tasks: bot-health-dispatch-only-reader-1186

- [x] 1. Add role-based pipeline selection (`workflow_triggers`, `watched_pipelines`) and per-event run reads in `scripts/bot_health.py`, keeping the cron-only helpers additive.
- [x] 2. Join `bot-health.yml` to `MAIN_PIPELINES` and `DISPATCH_ONLY_PIPELINES` in `scripts/pipeline_failure_issue.py`.
- [x] 3. Add RED-first guards to `tests/test_bot_health.py` and register them in its hand-rolled `main()`; verified RED on the pre-change seam (9 FAIL) and GREEN on the head (27 passed).
- [x] 4. Add the rule-6r wiring pin to `tests/test_workflows.py` and register it in `main()`; verified `python3 tests/test_workflows.py` → `PASSED 1311 | FAILED 0`.
- [~] 5. Update AGENTS.md §6b `bot-health.yml` bullet and §8 guard row — blocked: rule 3c human sign-off (AGENTS.md protected in a headless leg)
- [x] 6. Update ARCHITECTURE.md target/script/workflow rows and the Makefile help string; regenerate `OPENSPEC.md`.
- [x] 7. Run `make lint`, `make architecture-check`, `make openspec-check`, `make findings-check`, `python3 tests/test_workflows.py`, `make pr-message-check` and `make pr-closure` — all green.
- [x] 8. Compose the PR body, push the head, open the five-section PR with one `closes #1186`, record+archive the change and report the head SHA on the issue with handover to `tll-reviewer` — validated locally with `make pr-message-check` and `make pr-closure` (1 keyword, 1 reference).
