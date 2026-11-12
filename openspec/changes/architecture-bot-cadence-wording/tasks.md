# Tasks: architecture-bot-cadence-wording (#860)

- [x] Open the OpenSpec change (proposal, spec, tasks) and land the first unique commit
- [x] Rewrite the schedule comment in `.github/workflows/architecture-bot.yml`: Wednesday weekly cadence, odd-minute rationale kept
- [x] Relabel the cron check in `tests/test_architecture_bot.py` to the Wednesday weekly slot
- [x] Add `test_the_schedule_comment_names_the_cadence_it_pins`: shipped comment names the cadence, no HOURLY claim; the OLD comment text planted as a fixture goes RED (rule 6c) — verified against `git show origin/master~1:.github/workflows/architecture-bot.yml`: both problems fire
- [x] `tests/test_architecture_bot.py` 79/0 and `tests/test_workflows.py` 1015/0 on the host; CI runs `make test`, `make lint` and `make openspec-check` on this PR and auto-merge requires them green
- [x] PR opened with the five-section message pattern and the single `closes #860` claim (`make pr-message-check` OK), ready for review, monitored to green and auto-merge
