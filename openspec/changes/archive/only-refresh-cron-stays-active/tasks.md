# Tasks — only-refresh-cron-stays-active (#1029)

- [x] Strip `schedule:` from issue-bot, issue-review-bot, architecture-bot, bot-health,
      code-review-bot, pr-health, queued-alarm; strip `issues:` from issue-bot (keep owner
      `workflow_dispatch`) — verified: `tests/test_workflows.py` 1083 PASSED / 0 FAILED,
      incl. `test_only_the_refresh_pipeline_carries_a_schedule`
- [x] qa-validate: remove the `make hermes-smoke` step from `live-smoke`; NO agent/LLM
      target check added — verified in the same suite (`qa: NO hermes-smoke step`,
      `qa: the pipeline calls NO agent/LLM target anywhere`)
- [x] `scripts/sweep_alarm.py`: dispatch-mode awareness (`workflow_declares_schedule`) —
      no-owed-delivery OK, FAILED/HUNG dispatch red — verified:
      `tests/test_sweep_alarm.py` 45 PASSED / 0 FAILED
- [x] Flip the cadence pins in `tests/test_bot_health.py` and `tests/test_architecture_bot.py`
      (dispatch-only) — verified green (18/0, 79/0)
- [x] `AGENTS.md`: new rule 6t + §6b/§6e/§6j/§6l/§8 rows updated; new §8 guard row —
      verified: `tests/test_agents_rows.py` 79 PASSED / 0 FAILED
- [x] Regenerate `ARCHITECTURE.md` inventory block (`make architecture-refresh`) —
      verified: `tests/test_architecture_bot.py` + `tests/test_architecture.py` green
- [x] Regenerate README bot-cadence prose + `render_readme` template (dispatch-only fleet) —
      verified: `tests/test_readme_bot_cadence.py` + render suites green
- [x] `make lint` green (workflow-guard scan incl. the new trigger surfaces)
- [x] `findings.md` written (rule 6g)
- [x] Full `make test` green on the branch head
- [x] `make secret-scan` clean before push
- [x] PR opened with `closes #1029` and the five-section body (`make pr-message-check` local pre-validation)
- [x] `make openspec-record-pr ISSUE=1029 PR=<n>` archived this change at the PR head
