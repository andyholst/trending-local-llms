# Tasks: architecture-bot-cadence-wording (#860)

- [ ] Open the OpenSpec change (proposal, spec, tasks) and land the first unique commit
- [ ] Rewrite the schedule comment in `.github/workflows/architecture-bot.yml`: Wednesday weekly cadence, odd-minute rationale kept
- [ ] Relabel the cron check in `tests/test_architecture_bot.py` to the Wednesday weekly slot
- [ ] Add `test_the_schedule_comment_names_the_cadence_it_pins`: shipped comment names the cadence, no HOURLY claim; the OLD comment text planted as a fixture goes RED (rule 6c)
- [ ] `make test` + `make lint` green in the container; `make openspec-check` green
- [ ] PR with the five-section message pattern, `closes #860`, ready for review; monitor to green and auto-merge
