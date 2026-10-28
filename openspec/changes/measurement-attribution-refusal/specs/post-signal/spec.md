# post-signal

## ADDED Requirements

### Requirement: A placeholder post that claims engagement is a failure

`make validate` MUST FAIL a measurement whose `source_post` identifies no post (a bare
mirror link, a profile page, nothing) AND which carries a positive engagement count —
likes, comments, reshares or views. A placeholder with NO counts MUST stay a warning, so
the low-signal, static historical rows the issue's carve-out protects are never reded.

#### Scenario: a placeholder with counts

- **Given** a measurement whose `source_post` is `https://lightbrd.com/` and whose `likes`
  is 2
- **When** `check_post_signal` runs
- **Then** it adds a failure naming the model and the engine, and the reason says the count
  cannot come from a placeholder post
- **Test:** tests/test_post_signal.py::test_placeholder_with_engagement_counts_fails

#### Scenario: a placeholder without counts

- **Given** a measurement whose `source_post` is a placeholder and whose counts are all zero
- **When** `check_post_signal` runs
- **Then** it adds no failure (the low-signal row stays allowed)
- **Test:** tests/test_post_signal.py::test_placeholder_without_counts_stays_allowed

#### Scenario: coverage stays a warning

- **Given** a store at 0% real-post coverage
- **When** `check_post_signal` runs
- **Then** it prints a WARN line and adds no failure for the coverage itself
- **Test:** tests/test_post_signal.py::test_post_signal_coverage_never_fails
