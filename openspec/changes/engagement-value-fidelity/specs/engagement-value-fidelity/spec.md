# engagement-value-fidelity

## ADDED Requirements

### Requirement: flatten resolves each row's engagement exactly from posts.json

Every measurement row materialised by `flatten_store(catalog, measurements, posts)` must
carry engagement counters that equal, **value-for-value**, the canonical `posts[source_post]`
entry for each of the five counters (likes, comments, reshares, views, interactions). A row
whose `source_post` has no canonical post entry resolves each counter to 0. This is the
primary engagement-resolution contract of the normalised store (design #692); the
non-shrink guard (`check_no_value_loss`) remains and additionally protects the #463/#525/
#411/#650 loss classes against a future drop.

Value-for-value equality is what the rendered README's buzz/trend lines are derived from —
a corrected post entry re-resolves every referencing row, so the rendered lines are
**regenerated to the canonical value**, not claimed unchanged.

#### Scenario: every resolved row equals its canonical post entry value-for-value

- **Given** the shipped catalog, measurements and posts and every row resolved through `flatten_store`
- **When** each resolved row's five engagement counters are compared against `posts[source_post]` value-for-value
- **Then** the counters are exactly equal (not merely non-shrinking) for every row with a canonical post entry; rows without one resolve to 0
- **Test:** tests/test_measurements_split.py::test_flatten_engagement_equals_posts_value_for_value
