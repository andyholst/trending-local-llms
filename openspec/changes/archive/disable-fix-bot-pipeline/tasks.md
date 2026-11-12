# Tasks

- [x] 1. Delete `.github/workflows/fix-bot.yml` (pipeline, guard, dispatch + workflow_run triggers).
- [x] 2. `qa-validate.yml`: remove the `dispatch-fixbot` job; a red validate stays red and posts its report.
- [x] 3. `pr-health.yml` + `scripts/pr_health.py`: sweep becomes report-only; `MAX_FIXBOT_COMMITS` and the dispatch step removed; token wiring simplified to the default `github.token`.
- [x] 4. `refresh-bot.yml`, `issue-bot.yml`, `queued-alarm.yml`, `publish-agent-image.yml`: every "dispatch fix-bot" hint restated for the retired pipeline.
- [x] 5. `Makefile`: no recipe dispatches the retired pipeline; the fix-loop recipes stay as the implementer's.
- [x] 6. Scripts rewritten in place: `fix_loop.sh` caller doc, `qa_report.sh`, `master_alarm.py`, `bot_markers.py`, `check_commit_authorship.py`, `engine_registry.py`, `self_correct_raw.py`, `validate.py`, `nerve_key_check.py` — no dead references to the removed workflow remain.
- [x] 7. Tests updated in the same change (rule 6b): `test_workflows.py` (new `test_fix_pipeline_retired` guard; qa/loop/settings rewired), `test_pr_health.py`, `test_fix_loop.py`, `test_architecture.py`, `test_secret_output.py`, `test_nerve_key_wiring.py`.
- [x] 8. Verified GREEN on the host suites that cover the change: test_workflows 967/0, test_pr_health 41/0, test_architecture 67/0, test_secret_output 97/0, test_nerve_key_wiring 45/0, test_makefile_only 25/0, test_bot_markers 53/0, test_architecture_bot 76/0, test_master_alarm 24/0.
- [x] 9. `AGENTS.md` (rule 3c: this issue restates §6b pipeline list, §6j marker table and §8 guard rows): the fix-bot lines retire with the pipeline.
- [x] 10. `ARCHITECTURE.md` regenerated (`make architecture-refresh`) + prose fixed; `make architecture-check` green.
- [x] 11. `make openspec-index` + `make openspec-check` + `make lint` green; PR opened with the five-section body closing #814.
