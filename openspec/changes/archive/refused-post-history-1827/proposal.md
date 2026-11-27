# Proposal: refused-post-history-1827

Issue: #1827
PR: #1831

## Why

The write-time weight-gb contradiction refusal (`refuse_weight_gb_contradictions`,
`scripts/update_trending.py:2623-2644`) correctly keeps a contradictory value out
of canonical `engines` (`:3259`). But the source post of the row it refuses is a
rule-3b history post: the measurement stays in `measurements.json`, while the
post was deleted by the 30-day `prune_posts` (`:890-902`) called from
`recompute_7d_engagement` (`:923`). Measured on `a8d926d`: re-deriving the store
at the aggregate's clock (`2026-11-27`) left `history_row_present=True` but
`seen_post_present=False`, reddening the named guard at
`tests/test_weight_gb_contradiction.py:100-102`. History is never wiped.

## What Changes

- `prune_posts` gains one optional argument, `keep_urls`: a post older than
  `RETENTION_DAYS` is kept when its own `url` is in that set. No new key, flag or
  list on the post entry, no schema or data-shape change.
- `recompute_7d_engagement` passes the source-post URLs of the model's OWN stored
  engine measurements (rule-3b history) as `keep_urls`. No second history
  implementation: it reuses the existing `_collect_seen_posts` / `dedupe_posts`
  / `prune_posts` seam and the measurement rows already on the model.
- The contradiction stays refused at ingest and in the reader; `recent`'s
  7-day cutoff is untouched, so retained old history posts do not move ranks.
- The issue-#1182 legacy counters stay sourced from the retention-only view
  (`prune_posts(posts, today)` with no `keep_urls`), so a retained old history
  post never raises `likes`/`views` on any model.

## Impact

- `scripts/update_trending.py` — optional `keep_urls` parameter on `prune_posts`
  and one extra condition; one `history_urls` set built at the existing prune
  call site.
- `tests/test_7day_aggregation.py` — one new real-logic unit test for the seam,
  wired into `main()`; existing retention/boundary tests stay green.
- `openspec/changes/refused-post-history-1827/` + regenerated `OPENSPEC.md`.

## Not covered

- A *newly* refused row that is never stored as history: seeding its
  `source_post` into `seen_posts` at the refusal seam is a separate,
  independently shippable child. Do not re-admit the refused value into
  `engines` to keep its post.
- No `data/`, README, workflow, schedule or label change.
