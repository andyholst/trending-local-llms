## ADDED Requirements

### Requirement: The planner skill describes the store shape that actually exists

The `tll-planner` skill SHALL describe `data/models.json` as a top-level `engines` registry plus a
`models` **list**, with each model's per-(model, engine, source_post) measurement rows in
`engagement.seen_posts[]` (each row carrying `url`, `date`, `engine`, `tps`, `hardware`, `quant` and the
per-post counters). It SHALL NOT state that a model carries an `engines[]` array, that the rows are
"per-model `engines[]` rows", or that the count to watch is "inline rows". This keeps the planner's
store-size and sync-honesty judgement aligned with the shipped store after the #689 split.

#### Scenario: The shipped store puts measurements in seen_posts, not a model-level engines array

- **Given** the real `data/models.json` at `master`
- **When** a reader inspects a model row's keys and its `engagement` block
- **Then** the row has no `engines` key, and `engagement.seen_posts` is a non-empty list whose first
  row carries `url`, `date`, `engine`, `tps`, `hardware` and `quant`
- **Test:** tests/test_planner_skill_store_shape.py::test_store_measurement_rows_live_in_seen_posts_not_engines_array

#### Scenario: The skill never teaches the retired engines[] shape

- **Given** the real tracked `agents/tll-planner/skills/tll-planner/SKILL.md`
- **When** its text is checked for the measured `engagement.seen_posts[]` description and the retired
  phrasings
- **Then** it contains the `seen_posts[]` / `models`-is-a-list description and none of the stale
  "each model carries/has an `engines[]` array" or "per-model `engines[]` rows" statements
- **Test:** tests/test_planner_skill_store_shape.py::test_planner_skill_describes_the_real_store_shape
