## ADDED Requirements

### Requirement: The engine_min_version detector sees the build phrasings posts use

The data-gap analysis SHALL classify a model whose captured post states an engine
build or version in free text — a version beside an engine name, a `b<NNNN>`
llama.cpp build tag beside the engine name, a provenance phrase (`untouched
upstream`, `stock llama.cpp`, `submodule`, `from source`, `commit <hex>`), a version
beside an adapter/fork name, a `q4_0`-class KV-cache cache-type, or a native draft
statement — as prose-only ingest work (`unstructured`), not as "no captured post
states it". A bare capacity, quant name or speed with no engine/build word beside it
SHALL NOT count as a build claim.

#### Scenario: a captured post states the build in #214's wording

- **Given** a store model with no structured `engine_min_version` whose store and
  captured-measurement prose both read `BigMoeOnEdge on stock llama.cpp (untouched
  upstream, submodule)`
- **When** `analyse` runs over the store and the raw captures
- **Then** the model is in `unstructured:engine_min_version` and not in
  `not_captured:engine_min_version`
- **Test:** tests/test_data_gap_analysis.py::test_engine_min_version_detector_sees_the_build_phrases_posts_use

#### Scenario: an adapter version and a cache-type quant are build claims

- **Given** captured measurements reading `MLX 4-bit Swift 1.5 adapter` and `Q4_0 KV
  cache, native MTP draft` on models with no structured `engine_min_version`
- **When** `analyse` runs
- **Then** both models classify as prose-stated (`unstructured` or
  `captured_prose`), never as `not_captured`
- **Test:** tests/test_data_gap_analysis.py::test_engine_min_version_detector_sees_the_build_phrases_posts_use

#### Scenario: a capacity or quant name with no build word is not a claim

- **Given** a captured measurement reading `Q4_K_M (~14.6GB) on an RTX 4090 24GB, 150
  tok/s` with no engine version or provenance word
- **When** `analyse` runs
- **Then** the model stays in `not_captured:engine_min_version` (an acquisition gap)
- **Test:** tests/test_data_gap_analysis.py::test_engine_min_version_detector_sees_the_build_phrases_posts_use
