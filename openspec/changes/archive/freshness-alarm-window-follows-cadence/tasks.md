# Tasks: freshness-alarm-window-follows-cadence

- [x] `queued-alarm.yml` freshness step drops `MAX_AGE_HOURS=14`; comment restates the weekly default
- [x] `tests/test_freshness_alarm.py`: no-window-literal pin (workflow + recipe) and weekly boundary tests (132 h and 162 h green, 330 h red naming 170)
- [x] Tests RED on the pre-change workflow (1 FAIL on the `MAX_AGE_HOURS=14` literal, 18/19) and 19/19 green after
- [x] AGENTS.md §8 guard row added; ARCHITECTURE.md target row + inventory block updated (`make architecture-refresh`)
- [x] OpenSpec change (proposal, spec with per-scenario tests, tasks) + index regenerated
- [x] Local gates green (`make lint`, freshness suite, secret-scan; `make openspec-check` on the head once the PR box is ticked)
- [x] PR opened with the five-section body and `closes #1031` (PR #1034)
