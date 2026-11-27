# Tasks: rollup-history-counter-1847 (issue #1847)

- [x] T1: add one local `_counter_sum` helper in `recompute_7d_engagement` and the per-counter `sourced = _counter_sum(counted, counter) or _counter_sum(posts, counter)` fallback; keep `counted = prune_posts(posts, today)` primary, MAX never lowering, the no-invented-zero-key guard, rank inputs and the #1827 `keep_urls` block byte-unchanged.
- [x] T2: add `tests/test_rollup_history_counter_1847.py` (12 real-logic guards), RED-verified on a detached base tree with the run's raw snapshots: 4 FAIL including `no shipped row has a zero aggregate while its posts carry likes [43]`.
- [x] T3: regenerate `data/models.json`, `data/measurements.json`, `data/posts.json`, `README.md` and a fresh snapshot through the normal merge path with the run's 70 new raw snapshots; symptom 0, flash-next 19,516, #1182 16/0, #1847 12/0.
- [x] T4: sibling regressions green (engagement-contract 22/0, 7day 119/0, weight-gb 26/0, post-signal 39/0, measurements-split 626/0, cross-model 103/0, source-post-readback 26/0) and `make freshness-alarm` green with the landed snapshot.
- [x] T5: `findings/1847.md`, this change dir with `.openspec.yaml`, and a regenerated `OPENSPEC.md` index; no label, schedule, schema or contract change.
- [x] T6: READY PR with `Closes #1847` in both title and body, owner-authored commit, fast offline checks green, real CI verdict and issue-close verification reported on the issue thread.
