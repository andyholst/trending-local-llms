# Proposal: rollup-history-counter-1847

Issue: #1847
PR: #1849

## Why

Refresh run 46061634103 left 43 rows with `engagement.likes == 0` while their own `seen_posts` carried real likes. The #1827 rule-3b exemption keeps a stored measurement's old source post in `seen_posts`, but the #1182 counter loop re-prunes the list without `keep_urls`, so history-only liked posts never reach the grow-only counter. Replacing the retention view with the full list would over-count fresh rows (flash-next 19,516 → 31,186) and break #1182's value-for-value contract.

## What Changes

- `scripts/update_trending.py::recompute_7d_engagement`: add one local `_counter_sum(post_list, counter)` and, for each of `likes`/`comments`/`reshares`/`views`, source `sourced = _counter_sum(counted, counter) or _counter_sum(posts, counter)`. The retention-only `counted` view stays PRIMARY; the same already-deduped, already-history-pruned `posts` list is the fallback only when `counted` carries no signal. MAX still never lowers, the no-invented-zero-key guard is unchanged, rank inputs are untouched, and the #1827 `keep_urls` block is byte-identical.
- `tests/test_rollup_history_counter_1847.py`: 12 real-logic guards covering the history-only fallback, retention primacy, MAX, no invented key, shipped-store symptom, the pinned flash-next value, and wiring.
- `data/models.json` / `data/measurements.json` / `data/posts.json` / `README.md` / a fresh snapshot: regenerated through the normal merge path with the run's 70 new raw snapshots so store, render and snapshot agree.

## Impact

- Affected specs: `post-signal` (ADDED: a counter with no signal in the retention view is sourced from the retained rule-3b history posts).
- Affected code: scripts/update_trending.py, tests/test_rollup_history_counter_1847.py, the four generated data/doc artifacts and one snapshot.
- Not changed: schema, key set, counter definitions, rank semantics, `last_7d_likes`, `trend_score`, schedules, labels, or any second engagement implementation.

## Verification

- RED on base + run snapshots: `FAIL … [43]`, `FAILED 15 | FAILED 1`; new guard 4 FAIL.
- GREEN on the one-seam fix: #1182 16/0, #1847 12/0, symptom 0, flash-next 19,516; siblings 22/0, 119/0, 26/0, 39/0, 626/0, 103/0, 26/0; `make freshness-alarm` green with the landed snapshot.
