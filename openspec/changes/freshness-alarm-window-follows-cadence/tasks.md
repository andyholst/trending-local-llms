# Tasks: freshness-alarm-window-follows-cadence

- [ ] `queued-alarm.yml` freshness step drops `MAX_AGE_HOURS=14`; comment restates the weekly default
- [ ] `tests/test_freshness_alarm.py`: no-window-literal pin (workflow + recipe) and weekly boundary tests (165 h green, 180 h red naming 170)
- [ ] Tests RED on the pre-change workflow (the 14 h literal present) and green after
- [ ] AGENTS.md §8 guard row added
- [ ] OpenSpec change (proposal, spec with per-scenario tests, tasks) + index regenerated
- [ ] Local gates green (`make lint`, freshness suite, secret-scan, `make openspec-check`)
- [ ] PR opened with the five-section body and `closes #1031`
