# engine-figure-alignment

## ADDED Requirements

### Requirement: One declared spelling map resolves a captured engine name

A captured engine spelling that names a registered engine under another name MUST be
resolved through `scripts/engine_registry.ENGINE_NAME_ALIASES` — the ONE definition
(rule 6d) — and stored under the registered name; `make engine-check` must not WARN on
an aliased spelling, and an alias whose target is NOT registered keeps the loud WARN
(the map may never hide a genuinely unknown engine).

#### Scenario: the shipped raw captures resolve with zero engine-check warnings

- **Given** the shipped `data/raw/` captures naming `mlx.fast` and `Bonsai Oryon`
- **When** `engine_registry.check_raw` runs against the shipped store (offline fixture
  fetch)
- **Then** no decision is emitted for an aliased spelling, every decision that remains
  is `registered`, and every alias target is a registered engine carrying a repo url
  (rule 5b)
- **Test:** tests/test_engine_figure_alignment.py::test_the_engine_check_is_warn_free_on_the_shipped_raw_captures

#### Scenario: a planted captured spelling re-homes at ingest

- **Given** a fresh model row carrying measurements on `mlx.fast` and `Bonsai Oryon`
- **When** `update_trending.apply_engine_aliases` runs on it
- **Then** the engines read `MLX-fast (Bonsai 2)` and `llama.cpp (PrismML fork)`, the
  rename is idempotent, the model's own `engine_aliases` still win over the registry
  map, and `fabricated_engine_reason` returns None for the aliased spellings
- **Test:** tests/test_engine_figure_alignment.py::test_planted_captured_spellings_re_home_at_ingest

#### Scenario: the spelling map has one home and registered targets

- **Given** `scripts/engine_registry.py`
- **When** the suite reads `ENGINE_NAME_ALIASES` and the shipped store
- **Then** every alias target exists in `data/models.json` `engines` with a repo url, no
  alias key is itself registered, and the decision for each key is stated in the map's
  comment
- **Test:** tests/test_engine_figure_alignment.py::test_the_spelling_map_is_one_definition_with_registered_repo_linked_targets

### Requirement: The Bonsai Oryon rule decision is recorded in the registry

`Bonsai Oryon` is packaging, not an inference engine (it packages PrismML's llama.cpp
fork + ggml as one .deb; rule: harnesses/apps are never engines), so it is never
registered and its figures re-home to `llama.cpp (PrismML fork)` — the engine that
produced the captured 34.8 t/s. The decision is recorded in the registry entry's note.

#### Scenario: the registry names the decision

- **Given** the shipped `data/models.json` `engines` after this change
- **When** the registry entry for `llama.cpp (PrismML fork)` is read
- **Then** its note names `Bonsai Oryon` as packaging of the fork whose figures re-home
  there, and no `Bonsai Oryon` engine entry exists
- **Test:** tests/test_engine_figure_alignment.py::test_the_bonsai_oryon_decision_is_recorded_in_the_registry

### Requirement: A measurement shared across two model ids fails validation unless justified as data

A measurement `(engine, tps, date, source_post)` appearing under two model ids MUST fail
`make validate`, and a `(engine, tps, date)` shared between variant-related model ids
(one normalized id is a prefix of the other) MUST fail too — the variant-row trap where
hardware labels differ across variants. A pair may stay only when justified as DATA by
`measurement_model_aliases` on either row (the #652 exception vehicle, reviewable in the
store diff); an unrelated pair reporting the same figure on the same day from different
posts is a coincidence and stays legal. No shipped row is removed to pass the gate
(rule 3b).

#### Scenario: make validate fails on a planted cross-row duplicate

- **Given** a planted store where two model ids carry the identical
  `(engine, tps, date, source_post)` measurement
- **When** `check_no_duplicate_measurements` runs
- **Then** the gate records a failure naming both ids and the measurement
- **Test:** tests/test_engine_figure_alignment.py::test_make_validate_fails_on_a_planted_cross_row_duplicate

#### Scenario: a planted variant pair sharing engine, tps and date fails

- **Given** a planted store where `qwen3.8-27b-swift` carries the base row's engine, tps
  and date under a DIFFERENT source post and hardware label
- **When** `check_no_duplicate_measurements` runs
- **Then** the gate records a failure for the variant pair, and the same pair planted on
  two UNRELATED ids is not flagged
- **Test:** tests/test_engine_figure_alignment.py::test_a_planted_variant_pair_sharing_engine_tps_and_date_fails

#### Scenario: a justified pair passes the gate

- **Given** both planted duplicate shapes, each justified by a
  `measurement_model_aliases` entry on one row naming the counterpart
- **When** `check_no_duplicate_measurements` runs
- **Then** the gate is green, and `check_measurement_alias_map` accepts the exception
- **Test:** tests/test_engine_figure_alignment.py::test_justified_variant_and_bakeoff_pairs_pass_the_gate

#### Scenario: the shipped store has no undocumented cross-row duplicate

- **Given** the shipped `data/models.json` + `data/measurements.json`
- **When** `check_no_duplicate_measurements` runs over the real store
- **Then** zero failures are recorded — every shipped pair is justified as data
- **Test:** tests/test_engine_figure_alignment.py::test_the_shipped_store_has_no_undocumented_cross_row_duplicates
