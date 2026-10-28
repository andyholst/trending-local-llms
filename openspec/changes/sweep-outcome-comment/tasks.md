# Tasks

- [ ] 1. The change is tracked (this directory) before any code edit.
- [ ] 2. `scripts/bot_markers.py`: `issue-bot-outcome` registered (kind `outcome`) and listed as WRITTEN.
- [ ] 3. `scripts/sweep_outcome.py`: `owed()`, `comment_body()`, `--post` with per-run dedup, exit 2 on a refusal.
- [ ] 4. `make issue-outcome` — the only entry point, wired into the workflow.
- [ ] 5. `issue-bot.yml`: the `always()` step, gated on implement + not-closed + empty verdict.
- [ ] 6. `tests/test_sweep_outcome.py`: decision matrix, body/marker, dedup, loud refusals, through the real script.
- [ ] 7. `tests/test_workflows.py`: the shipped step (present, always, gated, default token, calls the target).
- [ ] 8. `AGENTS.md` §6j table row + §6e prose + §8 row.
- [ ] 9. `ARCHITECTURE.md` rows + §10 regenerated; `OPENSPEC.md` regenerated.
- [ ] 10. `make lint`, `make _validate`, `make _test`, `make architecture-check`, `make openspec-tasks-check`, `make openspec-index-check` green; `findings.md` written.
