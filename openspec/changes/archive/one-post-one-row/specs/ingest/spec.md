# ingest

## ADDED Requirements

### Requirement: One real post is one measurement per (engine, date)

Rows sharing a real `source_post`, the same `engine` and the same `date` MUST collapse into a
single stored measurement: the highest t/s kept, counters kept at their max, dimensions
fill-only.

#### Scenario: the measured four-row case

- **Given** four Ollama rows for one post and date, differing in hardware wording, t/s, `context_tokens` (66000/67000) and likes
- **When** they are collapsed
- **Then** one row remains, carrying t/s 43, `context_tokens` 66000 and likes 25
- **Test:** tests/test_one_post_one_row.py::test_the_measured_case_collapses_to_one_row

#### Scenario: different posts and different engines

- **Given** two rows from two different posts, and two engines on one post
- **When** they are collapsed
- **Then** two rows remain in each case
- **Test:** tests/test_one_post_one_row.py::test_different_posts_stay_distinct

### Requirement: A placeholder post is never a key

Rows whose `source_post` is not a `/status/<id>` URL MUST remain distinct, whatever their
engine and date.

#### Scenario: uncited rows

- **Given** a bare mirror link, an empty string and a missing `source_post`
- **When** they are collapsed
- **Then** all three rows remain
- **Test:** tests/test_one_post_one_row.py::test_a_placeholder_post_is_never_a_key

### Requirement: The ingest seam performs the collapse

`merge_engines` MUST collapse before its existing grouping, so a duplicate cannot reach the
store by the normal ingest path.

#### Scenario: merging an empty store with two rows from one post

- **Given** `merge_engines([], [row41, row43])` for one post
- **When** the merge runs
- **Then** one measurement is stored, with the higher t/s
- **Test:** tests/test_one_post_one_row.py::test_ingest_path_passes_through_the_collapse
