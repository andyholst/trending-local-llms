# post-signal

## ADDED Requirements

### Requirement: The counter mapping is named, not guessed

The `data-search` skill the search legs preload MUST state which rendered number is which
counter: a `…/status/<id>` post page renders its engagement counters in X's fixed order
**replies, retweets (stored as `reshares`), likes, views**; a search-result card renders the
same order with zero counters omitted, so a card showing fewer than four numbers is
ambiguous. A leg MUST open the cited post page whenever the card omits a counter it must
store, and MUST NOT take a counter from a neighbouring card.

#### Scenario: the skill names the order and the page rule

- **Given** the `data-search` skill the four search legs preload
- **When** `tests/test_post_signal.py` reads it
- **Then** it finds the fixed order stated (replies, retweets, likes, views), the
  card-omits-zeroes ambiguity, the open-the-post-page rule, and the no-neighbour-card rule
- **Test:** tests/test_post_signal.py::test_prompts_ask_for_post_url

### Requirement: The coverage report shows posts-with-views

`check_post_signal` MUST print, on the same report line it already prints for real post
URLs and engagement counts, the coverage of measurements whose `views` count is positive —
so a store whose captures default views to zero is visible in `make validate`. It stays
report-only (a WARN), never a failure.

#### Scenario: a store with views-zero captures reports it

- **Given** a store where one real-post measurement has `likes > 0` but `views == 0`
- **When** `check_post_signal` runs
- **Then** its line prints `with views` coverage and adds no failure
- **Test:** tests/test_post_signal.py::test_post_signal_coverage

#### Scenario: the helper returns the views count

- **Given** the fixture store
- **When** `post_signal_coverage` is called
- **Then** it returns a 4-tuple (total, real-post URLs, with any count, with views)
- **Test:** tests/test_post_signal.py::test_post_signal_coverage
