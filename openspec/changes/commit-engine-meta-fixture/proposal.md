# Proposal: commit-engine-meta-fixture

Issue: #505

## Why

The refresh aggregate runs `make engine-meta-capture` in its "Merge + validate
+ test" step, writing `tests/fixtures/github_meta.json` (the offline input
`tests/test_engine_registry.py` classifies a newly registered engine against,
per issue #334). But the commit step's change check and its `git add` list both
named only `README.md data/models.json data/snapshots data/raw
data/gap_baseline.json`, so the captured metadata was never in the PR and the
next run re-captured it from scratch. The runner's capture proved the engine
and then threw the proof away: qa-validate's `make test` on the PR ran without
the fixture, which is exactly the red `make test` #334 meant to prevent. A
meta-only change (an engine registered, no data figure) also printed "No data
changes" over a dirty tree.

`scripts/refresh_base.py` already lists `tests/fixtures/github_meta.json` in
both `GENERATED_PATHS` and `KEEP_PATHS`, so the sync half survives; only the
commit half was missing.

## What Changes

- **`.github/workflows/refresh-bot.yml`** — the refresh `aggregate` commit
  step names `tests/fixtures/github_meta.json` in BOTH its change check
  (`git diff --quiet -- …`) and its `git add …` list, so a refresh that
  registered an engine commits the fixture it captured, and a meta-only change
  still opens a PR. Same shape as the `data/gap_baseline.json` guard (#152).
- **`tests/test_engine_registry.py`** — the existing
  `test_capture_meta_keeps_the_fixture_covering_the_registry` now also asserts
  that the commit step's change check and its `git add` both name the fixture
  path, so a refresh PR always carries the captured metadata.

## Impact

`.github/workflows/refresh-bot.yml` (one step's two lists), the OpenSpec change
+ `OPENSPEC.md`. No `scripts/`, no `data/**` change.

## Not covered

- Re-capturing an existing fixture entry's stale description/topics — already
  out of scope for the capture itself (#334).
- Moving the commit path — the fixture stays `tests/fixtures/github_meta.json`
  exactly where `scripts/engine_registry.py` (`META_FIXTURE`) reads it.
