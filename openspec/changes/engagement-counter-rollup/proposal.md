# Proposal: engagement-counter-rollup

Issue: #1182
PR: (unset until opened)

## Why

Measured 2026-11-21 in the shipped store: 56/120 rows had `engagement.likes == 0` while their
`seen_posts` summed real likes; `qwen3.8-flash-next-125b` held 47 posts summing 19,516 likes /
319 comments / 210 reshares / 117,971 views with every model-level aggregate at 0. A counter
declared grow-only sitting at 0 while its own sources carry values is invisible corruption
(rule 3b). The issue's original ranking claim was corrected on its thread: the tables rank by
`trend_score`/`posts_7d` (7-day post buzz), NOT by these legacy cumulative fields — so this
change repairs the data honestly without claiming it changes the list. The capture hole that
actually drops flash-next from the 🔥 tiers is #1183 (companion PR).

## What Changes

- `scripts/update_trending.py::recompute_7d_engagement`: raise the four legacy cumulative
  counters (`likes`, `comments`, `reshares`, `views`) to at least the sum of the deduped,
  pruned `seen_posts`, using MAX so an ingest-provided higher value is never lowered (rule 3b).
  Non-numeric post counters fail closed to 0 for that post; no value is invented (rule 2).
  `last_7d_likes` stays `posts_7d` and `trend_score` stays buzz-derived — rank semantics are
  deliberately unchanged.
- `data/models.json`: additive repair — 220 counter raises across 68 rows (flash-next likes
  0 → 19,516); no key/value shrinks; `README.md` re-rendered via `--render-only`.
- `tests/test_engagement_rollup_1182.py`: 11 checks (rollup, MAX, no invented value, locked
  rank semantics, shipped store, RED on the pre-change seam, wiring).

## Impact

- Affected specs: `post-signal` (ADDED: cumulative engagement counters are the additive max
  of their source posts and any higher stored value).
- Affected code: scripts/update_trending.py, data/models.json, README.md,
  tests/test_engagement_rollup_1182.py.
- Not covered: the rank/capture hole (#1183, companion PR), re-running the refresh
  (owner/cron only), and any change to `last_7d_likes`/`trend_score` semantics.

## Verification

New suite 11/11; `test_7day_aggregation.py` 114/0; `test_cross_model_attribution.py` 98/0;
`test_engine_figure_alignment.py` 32/0; `validate --only data` QA PASSED; lint green.