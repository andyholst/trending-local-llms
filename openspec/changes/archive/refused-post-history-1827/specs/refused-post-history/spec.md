## ADDED Requirements

### Requirement: A source post of a stored measurement survives the retention prune

The 30-day prune SHALL retain a `seen_posts` entry whose own `url` is the
`source_post` of one of the model's own stored engine measurements, even when
that measurement's stated value was refused at ingest. The exemption SHALL be
an optional `keep_urls` set passed to `prune_posts`, adding no key, flag or list
to the post entry and changing no stored shape.

#### Scenario: A refused value stays canonical-refused while its history post stays seen

- **Given** `bonsai-2-9b` with the `~493GB NVFP4` row from the Chahatusharma post stored as history and a re-derive clock past `RETENTION_DAYS`
- **When** the store is re-derived through `load_store -> sort_models -> split_store`
- **Then** the contradictory value is still absent from canonical/rendering measurements and the post is still in `engagement.seen_posts`
- **Test:** tests/test_weight_gb_contradiction.py::test_the_shipped_bonsai_row_is_corrected

#### Scenario: Only backed history is exempt, not every old post

- **Given** a post older than 30 days that is a stored measurement's `source_post`, an unrelated post older than 30 days with no backing measurement, and a fresh post
- **When** engagement is recomputed for that model
- **Then** the backed post survives, the unrelated old post is still pruned, the fresh post is unaffected, and `posts_7d` is unchanged (the 7-day cutoff did not move)
- **Test:** tests/test_7day_aggregation.py::test_prune_posts_keeps_stored_history_url_but_prunes_unrelated_old_post

### Requirement: The contradiction is still refused and named

The write-time refusal SHALL keep the contradictory measurement out of
canonical `engines`, and SHALL name the source post and both footprints in the
refusal, whether checked directly or through a re-capture at ingest.

#### Scenario: The shipped row is refused directly with both footprints named

- **Given** the exact `bonsai-2-9b` MLX 36 `~493GB NVFP4` re-capture as a new raw row
- **When** `refuse_weight_gb_contradictions` runs
- **Then** the row is refused, nothing is kept, and the refusal names the post and both `~493GB NVFP4` and `2.0GB (ternary)`
- **Test:** tests/test_weight_gb_contradiction.py::test_the_shipped_bonsai_row_is_refused

#### Scenario: A re-capture is refused at ingest while a legitimate row merges

- **Given** the same re-capture plus a legitimate fresh ternary measurement on that raw row
- **When** `ingest_raw_snapshots` runs
- **Then** the contradictory measurement is refused and never merges while the legitimate measurement still merges
- **Test:** tests/test_weight_gb_contradiction.py::test_ingest_refuses_a_re_capture_before_it_merges

### Requirement: Retention and rank are unchanged for everything else

The exemption SHALL NOT become a blanket retention override: the existing
30-day boundary and the 7-day aggregation contract stay byte-stable.

#### Scenario: Unrelated old posts are still pruned at the 30-day boundary

- **Given** a 31-day-old post and a 29-day-old post with no backing stored measurement
- **When** engagement is recomputed
- **Then** the 31-day-old post is dropped, the 29-day-old post is kept, and the model row is untouched
- **Test:** tests/test_7day_aggregation.py::test_prune_posts_retains_30d_removes_older

#### Scenario: The exactly-30-day boundary is unchanged

- **Given** posts at the exact 30-day boundary and one day beyond it
- **When** `prune_posts` runs with no backing history URL
- **Then** the boundary post is kept and the beyond-boundary post is dropped exactly as before
- **Test:** tests/test_7day_aggregation.py::test_prune_posts_boundary_30_days

#### Scenario: The engagement contract is unchanged

- **Given** the store after the additive prune-seam change
- **When** the engagement contract checks run
- **Then** the contract keys still cover the search contract and no dimension field is pruned
- **Test:** tests/test_engagement_contract.py::test_contract_keys_cover_search_contract

### Requirement: Retained history posts do not move the legacy counters

The issue-#1182 cumulative counters SHALL stay sourced from the retention-only
view exactly as before the exemption: a post kept solely because its URL is a
stored measurement's `source_post` is older than `RETENTION_DAYS` and SHALL NOT
contribute likes, comments, reshares or views.

#### Scenario: A retained old history post does not raise a stored counter

- **Given** a >30d history post with 100 likes backed by a stored measurement, an unrelated >30d post, and a fresh post with 5 likes
- **When** engagement is recomputed for that model
- **Then** the stored `likes` counter is 5 from the fresh post, the history post's 100 likes are not sourced, and the history post is still in `seen_posts`
- **Test:** tests/test_7day_aggregation.py::test_prune_posts_keeps_stored_history_url_but_prunes_unrelated_old_post

#### Scenario: The shipped store still equals the rollup output

- **Given** the shipped store after the additive change
- **When** the issue-#1182 rollup check runs
- **Then** every stored counter equals what the render seam computes, value for value
- **Test:** tests/test_engagement_rollup_1182.py::test_stored_counters_equal_the_rollup_output
