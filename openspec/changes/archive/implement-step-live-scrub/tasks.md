# Tasks

- [x] 1. The tracked change exists (this directory) before any code edit
- [x] 2. `Makefile`: `implement-issue`, `review-issue`, `review-issue-window` run their `$(DOCKER_RUN)` through `$(call scrubbed_run, …)` with per-target `HERMES_LOG` / `HERMES_LOG_SCRUBBED` and the agent's rc through `bash -o pipefail`
- [x] 3. `scripts/check_secret_output.py`: the three targets join `AGENT_TARGETS_TO_SCRUB` (ONE list), so `agent-target-does-not-scrub` refuses a recipe that drops the seam
- [x] 4. `issue-bot.yml` `Implement the issue` and both `issue-review-bot.yml` agent steps run their target uncaptured; the rc contracts (`rc=$?`, `exit $rc`, rc=3 `::error::`) and the artifact paths are unchanged
- [x] 5. `tests/test_implement_stream.py` (new): step text read from the workflows, a line on the console before the agent exits, rc survives the pipe, every spelling masked while streaming, both captures honest, reviewer detach contract — wired into `make test` (rule 6d)
- [x] 6. `tests/test_scrub_log.py` stub `make` emits through the real seam (self-scrubbing target); `tests/test_secret_output.py` matrix fixture seeds the guard's OWN list; `tests/test_workflows.py` `test_issue_bot_scrubs_the_agent_stream_before_it_reaches_the_log` asserts the new shape
- [x] 7. Verified RED against the shipped post-mortem shape (the step-text checks failed 3/35 before the workflow edit; the guard's `agent-target-does-not-scrub` fired while the recipes lacked the seam) and GREEN after
- [x] 8. `make architecture-refresh` regenerated the §10 block (the jobs' `make` calls changed) and `make architecture-check` passes; `make openspec-index` regenerated `OPENSPEC.md`
- [x] 9. `make lint` (incl. `check-secret-output`, workflow guards, pytest-import guard, working files) and `make test` pass
- [x] 10. `make openspec-check` green; PR opened with the five-section body; `PR:` row recorded here before auto-merge
