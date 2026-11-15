# Agents run bot work on the host — never dispatch CI pipelines

**Issue:** [#1055](https://github.com/andyholst/trending-local-llms/issues/1055)
**Capability:** `fleet-cadence`

## Why

Rule 6t already said "the agent (a Hermes session) never starts a CI pipeline", yet an
attended host sweep dispatched `issue-bot.yml` **five times in one day** (runs
43731335295, 43734140050, 43740810949, 43745032134, 43749254962 — the last cancelled
mid-flight) to drain the issue queue. A rule with no test is a convention, and the
convention broke the same day it was cited. The owner directive of 2026-11-15 is
therefore stated in full in §6t(e): bot pipelines are fired **only** by the human's
dispatch or the remaining cron; when an agent is asked to implement, review, sweep or
gather, the agent IS the bot, locally — its own worktree (rule 6n), the very targets
the bots run inside CI, a feature branch, a reviewed PR.

## What Changes

- `AGENTS.md` §6t(e) is rewritten to state both halves explicitly: no agent dispatch
  (`gh workflow run`, re-runs, dispatched sweeps), and the host path named by its
  targets (`make implement-issue`, `make review-issue`, the `search-*` legs,
  `make pr-health`, the §6s fixes). (Rule 3c: this issue's rulebook diff is §6t only,
  mandated by the owner directive; the attended run carries the human sign-off.)
- `tests/test_workflows.py` gains `test_agents_md_forbids_an_agent_dispatching_a_pipeline`,
  pinned at the wording, so the clause cannot be dropped or weakened silently.

## Impact

- Rulebook: `AGENTS.md` §6t(e).
- Tests: `tests/test_workflows.py` (new test, called from `main()`).
- No pipeline YAML, Makefile or data change: the cadence itself (dispatch-only +
  the refresh cron) already matches the directive.

## Not covered

- Removing the CI implement/review jobs themselves — they stay for the human's own
  dispatches (rule 6t(d)); only the agent's door to them is closed.
- The queue's scheduled draining — that is the owner's dispatch/cron cadence, unchanged.
