# Spec delta: post-signal (rollup-history-counter-1847)

## ADDED Requirements

### Requirement: Retained rule-3b history posts backstop the engagement counter rollup
The post-refresh rollup SHALL keep the retention-only `counted` view as the primary source of each legacy cumulative counter (`likes`, `comments`, `reshares`, `views`). When that view carries no signal for a counter, the rollup SHALL source the counter from the SAME deduplicated, history-pruned `seen_posts` list that is already stored on the row — including posts retained solely because they are a stored measurement's source URL (rule 3b, issue #1827). A single sum implementation SHALL serve both views; non-numeric values SHALL be ignored for that post; MAX SHALL never lower a higher stored value; a counter absent from a row with no signal SHALL stay absent (rule 2). Rank inputs (`trend_score`, `posts_7d`, `last_7d_likes`) SHALL be unchanged, and the retained history post SHALL remain in `seen_posts`.

#### Scenario: a history-only row sources its counters and keeps the post
- **Given** a row whose only counter-bearing seen_post is older than RETENTION_DAYS and retained by its own measurement's source_post, carrying 500 likes / 20 comments / 5 reshares / 3000 views
- **When** recompute_7d_engagement runs
- **Then** the four counters take those sums and the old post is still in seen_posts
- **Test:** tests/test_rollup_history_counter_1847.py::test_history_only_counter_is_sourced_and_post_retained

#### Scenario: the retention view stays primary
- **Given** a row with a fresh post carrying 120 likes and an old history post carrying 500 likes
- **When** recompute_7d_engagement runs
- **Then** likes is 120, not 620 — the whole-list fallback applies only when the retention view has no signal
- **Test:** tests/test_rollup_history_counter_1847.py::test_retention_view_stays_primary

#### Scenario: a higher stored value is never lowered on the fallback path
- **Given** a row with stored likes 5000 whose only liked posts are history posts summing 500
- **When** the rollup runs
- **Then** likes stays 5000
- **Test:** tests/test_rollup_history_counter_1847.py::test_max_is_never_lowered_on_the_fallback_path

#### Scenario: the fallback invents no key and lowers no rank value
- **Given** a history-only row with no `reshares` key on the row or its post
- **When** the rollup runs
- **Then** `reshares` stays absent while the other counters still roll up, and last_7d_likes stays equal to posts_7d
- **Test:** tests/test_rollup_history_counter_1847.py::test_fallback_does_not_invent_an_absent_key

#### Scenario: the regenerated store has no zero aggregate beside liked posts
- **Given** the store regenerated from the base plus refresh run 46061634103's raw snapshots
- **When** the real store guard reads data/models.json
- **Then** zero rows have a zero aggregate while their posts carry likes, and flash-next still stores 19,516 likes
- **Test:** tests/test_engagement_rollup_1182.py::test_the_shipped_store_carries_the_repair
- **Test:** tests/test_rollup_history_counter_1847.py::test_flash_next_pinned_counter_is_preserved
