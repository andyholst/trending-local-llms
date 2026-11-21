# Tasks: stale-last-seen-gap (issue #1183)

- [x] T1: `stale_last_seen(store)` in scripts/data_gap_analysis.py — store-wide-newest clock, 7-day threshold from update_trending.TRENDING_WINDOW_DAYS, same-base sibling evidence, no invented values.
- [x] T2: analyse() report key + ONE `stale_last_seen` signature entry; issue BODY section with per-row evidence; existing per-entry dedup marker applies.
- [x] T3: tests/test_stale_last_seen_gap.py (17 checks, including the shipped store and RED on the pre-change analysis).
- [x] T4: regressions — data_gap_analysis 330/330, validate --only data QA PASSED, lint green.
- [x] T5: PR opened, `make pr-message-check`, `make openspec-record-pr ISSUE=1183 PR=#1216` at the PR head.