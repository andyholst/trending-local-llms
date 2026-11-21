# Spec delta: post-signal (engagement-counter-rollup)

## ADDED Requirements

### Requirement: Cumulative engagement counters are the additive max of their source posts
The post-refresh rollup SHALL raise each legacy cumulative counter (`likes`, `comments`,
`reshares`, `views`) on a model row to at least the sum of that value across the deduped,
retention-pruned `seen_posts`, and SHALL NEVER lower a higher value already stored (rule 3b:
a grow-only counter may only rise). Non-numeric post values SHALL be ignored for that post, and
a row with no source posts SHALL gain no counter value (rule 2: invent nothing). The rank
SHALL be unaffected: `last_7d_likes` remains the count of posts inside the trending window and
`trend_score` remains derived from 7-day post buzz; the cumulative counters are data truth,
not sort keys.

#### Scenario: a zero aggregate is raised from its posts
- **Given** a row with likes=0 and two seen_posts carrying 120 and 77 likes
- **When** recompute_7d_engagement runs
- **Then** the row's likes becomes 197, comments/reshares/views take their post sums, and last_7d_likes still equals posts_7d
- **Test:** tests/test_engagement_rollup_1182.py::test_counters_are_raised_from_the_posts_they_store

#### Scenario: a higher stored value is never lowered
- **Given** a row with likes=5000 whose posts carry 120 and 77 likes
- **When** the rollup runs
- **Then** likes stays 5000 (MAX, additive only)
- **Test:** tests/test_engagement_rollup_1182.py::test_an_existing_higher_value_is_never_lowered

#### Scenario: no posts means no invented value
- **Given** a row with an empty seen_posts array
- **When** the rollup runs
- **Then** all cumulative counters and last_7d_likes stay 0
- **Test:** tests/test_engagement_rollup_1182.py::test_a_row_with_no_posts_keeps_zeros

#### Scenario: the shipped store is repaired
- **Given** the corrected data/models.json
- **When** the guard reads it
- **Then** flash-next stores 19,516 likes and no row has a zero aggregate while its posts carry likes
- **Test:** tests/test_engagement_rollup_1182.py::test_the_shipped_store_carries_the_repair