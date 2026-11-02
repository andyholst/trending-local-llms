# catalog-measurements

## ADDED Requirements

### Requirement: The catalog no longer inlines measurement rows

`data/models.json` is written as the compact catalog: each model row carries its identity
and footprint fields, the top-level `engines` registry and the per-model `engagement`
aggregate, but NO inline `engines[]` array. `split_store()` is the one definition of the
split and `load_store()` reconstructs the flat reader view.

#### Scenario: the shipped catalog has no inline engines

- **Given** the shipped `data/models.json`
- **When** `load_store()` materialises the reader view from catalog + measurements + posts
- **Then** no model row carries an `engines[]` key, yet every model + its measurements are
  reachable on load
- **Test:** tests/test_measurements_split.py::test_catalog_has_no_inline_engines

### Requirement: Each measurement resolves engagement once from posts.json

Engagement counters (likes/comments/reshares/views/interactions) are published once per
source_post in `data/posts.json` and referenced (not copied) by every measurement row in
`data/measurements.json`. A corrected like count edits one post entry and every referencing
row sees it; a measurement whose source_post has no post entry resolves engagement to 0,
never a penalty.

#### Scenario: a corrected engagement reaches every referencing row

- **Given** a measurement row whose source_post is shared by several rows
- **When** `flatten_store()` splices engagement in from posts.json
- **Then** every referencing row reflects the one post entry
- **Test:** tests/test_measurements_split.py::test_engagement_resolved_once_from_posts

### Requirement: The flattened view equals the old inline view

`flatten(catalog, measurements, posts)` reconstructs, per model, exactly the old inline
`engines[]` rows — engines[i] == measurements[model.id][j] ++ engagement(posts[source_post]).
`check_no_value_loss`/`check_split_flatten` guard this: no (model, engine, source_post)
measurement is dropped and no counter shrinks (the #463/#525/#411/#650 loss classes).

#### Scenario: the guard is green on the shipped store

- **Given** the shipped catalog + measurements + posts and the flat snapshots
- **When** the flattened view is compared against the old inline view
- **Then** every measurement row and its engagement survive (no value lost)
- **Test:** tests/test_measurements_split.py::test_flatten_equals_old_inline_guarded

### Requirement: The renderer materialises catalog x measurements with unchanged ranking

`render_readme()` materialises the flat view from `load_store()` and exercises the existing
`measurement_backend`/`best_measurement`/`in_scope`/`fits_tier` unchanged: highest t/s per
(model, engine, vram/ram-fit) sorts top exactly as before, and footprint-aware card-fit tables
keep reading the same per-row evidence.

#### Scenario: render via load_store is byte-identical

- **Given** the same flat store
- **When** `render_readme(load_store(catalog, measurements, posts))` runs
- **Then** best-t/s ranking and card-fit rows match the flat-store render
- **Test:** tests/test_measurements_split.py::test_renderer_materialises_same_ranking

### Requirement: The engine support-surface reads the same store

The engine support-surface tables (`measured_backends`, backend derivation, supported-engine
coverage — issue #338) read the same `flatten(catalog, measurements, posts)` view as the
renderer, so nothing about backend derivation or supported-engine coverage changes.

#### Scenario: backends derive from the flattened store

- **Given** a model with measurements across backends
- **When** backend/support-surface derivation runs on the flattened view
- **Then** the derived backends match the flat-store derivation
- **Test:** tests/test_measurements_split.py::test_support_surface_reads_same_store
