# Tasks: refused-post-history-1827

- [x] `prune_posts` (`:890`) gains optional `keep_urls`; a >30d post is kept when its own `url` is in that set — RED probe on base raised `TypeError`, GREEN on fix
- [x] `recompute_7d_engagement` (`:923`) passes the model's own stored-engine `source_post` URLs as `keep_urls`; no new key/flag/list, no second history implementation (rule 6d)
- [x] Refused value stays out of canonical `engines`; reader-side refusal and `recent`'s 7-day cutoff unchanged — `test_weight_gb_contradiction.py` 26/0 after re-derive on fix
- [x] New real-logic seam test in `tests/test_7day_aggregation.py` wired into `main()`: RED on base (history post pruned), GREEN on fix; whole module 118/0; `test_engagement_contract.py` 22/0
- [x] Unrelated old post still prunes at the 30-day boundary — `test_prune_posts_retains_30d_removes_older` and `test_prune_posts_boundary_30_days` stay green
- [x] `findings/1827.md` written; OpenSpec change (`.openspec.yaml`, proposal, spec with resolving `Test:` lines, ticked tasks) added and `OPENSPEC.md` regenerated
- [x] One READY PR with the five-section body and `Closes #1827` in both title and body; fast offline checks only, no merge/master push/schedule/label
- [x] #1182 legacy counters sourced from the retention-only view (`prune_posts(posts, today)` without `keep_urls`); `test_engagement_rollup_1182.py` 16/0 after CI exposed a second-order red, with a new assertion that is RED (105 vs 5) when the guard line is removed
