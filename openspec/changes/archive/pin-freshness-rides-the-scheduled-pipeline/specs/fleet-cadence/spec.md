# fleet-cadence

## ADDED Requirements

### Requirement: the agent-pin freshness verdict runs on the cadence that actually arrives

`make hermes-pin-freshness` (issue #1091, rule 6k) MUST run as a job of `refresh-bot.yml` — the
repository's only scheduled pipeline (rule 6t) — gated by that pipeline's `guard` job (rule 6j),
with a job-level `permissions:` block of `contents: read` + `issues: write` so the job can file the
drift issue, filing with the default `github.token` and never the owner PAT, and running the
target through the Makefile exactly once. It MUST NOT be a step of the dispatch-only
`queued-alarm.yml` sweep (owner ruling on issue #1093): a dispatch-only pipeline has no cadence
GitHub owes it, so a cadence-bound alarm placed there signals only when a human happens to
dispatch it.

#### Scenario: the scheduled pipeline carries the make-wired job

- **Given** `refresh-bot.yml`'s jobs
- **When** the wiring guard asks which pipeline compares the Hermes agent pin with the upstream
  release channel
- **Then** `pin-freshness` is a job that `needs: guard`, can write issues, names exactly ONE step
  `make hermes-pin-freshness REPO=…` with `GH_TOKEN: github.token`, and the guard is green
- **Test:** `tests/test_hermes_pin_freshness.py::test_the_scheduled_pipeline_calls_the_target_and_a_makeless_step_is_refused`

#### Scenario: the dispatch-only sweep may not re-adopt the cadence

- **Given** a planted `queued-alarm.yml` whose sweep gains a `hermes-pin-freshness` step again
- **When** the same wiring guard runs
- **Then** it refuses, naming the job and that the owner moved the step to the scheduled pipeline
- **Test:** `tests/test_hermes_pin_freshness.py::test_the_scheduled_pipeline_calls_the_target_and_a_makeless_step_is_refused`

#### Scenario: an ungated, unfileable or Makefile-bypassing job is refused

- **Given** planted shapes of the same job — no `needs: guard`, no `issues: write`, or a
  `run:` that calls `scripts/hermes_pin_freshness.py` directly
- **When** the same wiring guard runs
- **Then** each shape goes RED naming its defect, and no workflow anywhere in the tree names the
  script past the Makefile
- **Test:** `tests/test_hermes_pin_freshness.py::test_the_scheduled_pipeline_calls_the_target_and_a_makeless_step_is_refused`
