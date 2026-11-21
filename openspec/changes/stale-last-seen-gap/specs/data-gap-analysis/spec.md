# Spec delta: data-gap-analysis (stale-last-seen-gap)

## ADDED Requirements

### Requirement: A stale last_seen with a newer same-base sibling is a declared gap
The post-refresh analysis SHALL detect a store row whose newest captured post is older than
the store-wide newest `last_seen` by more than `update_trending.TRENDING_WINDOW_DAYS` when
another row naming the SAME base family has newer captured evidence, and SHALL declare it as
one additive acquisition gap. The store-wide newest SHALL be the clock — never the wall clock,
and no date or value SHALL be invented (rule 2). The finding SHALL carry the row id, its
`last_seen`, the lag in days, the store-wide newest, and the sibling id plus its date. There
SHALL be exactly ONE signature entry for the whole class (never one per model — the #472
re-filing churn), with the per-row evidence in the report and issued BODY; dedup SHALL use
the existing per-entry signature marker. The gap SHALL be additive (rule 3b): it reports a
capture hole and NEVER shrinks a row, re-sorts history, or changes the ranking.

#### Scenario: a stale row with a newer same-base sibling is declared once
- **Given** a row `qwen3.8-flash-next-125b` last seen 2026-11-08, an `Edge0-145B
  (Qwen3.8-Flash-Next base)` row last seen 2026-11-16, and a store newest of 2026-11-17
- **When** stale_last_seen runs
- **Then** exactly one finding names the stale row, a 9-day lag, and the Edge0 sibling; analyse adds `stale_last_seen` to the signature once; the issue body carries the marker
- **Test:** tests/test_stale_last_seen_gap.py::test_stale_row_with_a_newer_same_base_sibling_is_detected

#### Scenario: no false positives
- **Given** a row inside the 7-day window, or a stale row with no newer same-base sibling, or a sibling that names an unrelated base
- **When** stale_last_seen runs
- **Then** no finding is produced
- **Test:** tests/test_stale_last_seen_gap.py::test_no_false_positives

#### Scenario: the shipped store surfaces the real gap and the guard is new
- **Given** the shipped data/models.json with seven flash-next rows and Edge0 trending on 2026-11-16
- **When** the guard runs
- **Then** the flash-next rows are declared stale with the Edge0 evidence, and the pre-change analysis (git show origin/master) has no such signal
- **Test:** tests/test_stale_last_seen_gap.py::test_the_shipped_store_surfaces_the_real_flash_next_gap