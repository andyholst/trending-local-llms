# Tasks: Hermes pin freshness rides the ONE scheduled pipeline (issue #1093)

- [x] `refresh-bot.yml` gains a `pin-freshness` job: `needs: guard`, `permissions: contents: read`
  + `issues: write`, default `github.token`, one `make hermes-pin-freshness REPO=…` step
  (VERIFIED: `python3 tests/test_hermes_pin_freshness.py` → 59 checks green; `make
  check-workflow-guards` green with the new job gated by `guard`).
- [x] `queued-alarm.yml` drops the step and keeps a comment naming the ruling and the new home
  (VERIFIED: the wiring guard's planted "cadence crept back into the sweep" shape goes RED, the
  real sweep is clean).
- [x] The wiring guard is ONE seam with planted reds for every escape shape (makeless step,
  dropped job, ungated job, unfileable job, re-adopted cadence)
  (VERIFIED: `tests/test_hermes_pin_freshness.py::test_the_scheduled_pipeline_calls_the_target_and_a_makeless_step_is_refused`
  — and the whole module is RED when run against `origin/master`'s two workflow files).
- [x] `ARCHITECTURE.md` §6a target row, the `queued-alarm` alarm-job prose and the `refresh-bot`
  job description carry the new home + the ruling; `make architecture-refresh` regenerates the
  inventory block and `make architecture-check` is green
  (VERIFIED: `make architecture-check`).
- [x] Suite + gates green: `make test`, `make lint`, `make openspec-check`
  (VERIFIED: the run recorded on the PR).
- [x] The owner's ruling is recorded on issue #1093 and in `ARCHITECTURE.md`
  (VERIFIED: the comment on #1093 and the §6a row).
