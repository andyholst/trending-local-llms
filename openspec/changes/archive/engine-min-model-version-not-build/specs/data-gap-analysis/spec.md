# data-gap-analysis

## MODIFIED Requirements

### Requirement: The engine_min_version detector sees the build phrasings posts use

The data-gap analysis SHALL classify a model whose captured post states an engine
build or version in free text — a version beside an engine name, a `b<NNNN>`
llama.cpp build tag beside the engine name, a provenance phrase (`untouched
upstream`, `stock llama.cpp`, `submodule`, `from source`, `commit <hex>`), a version
beside an adapter/fork name, a `q4_0`-class KV-cache cache-type, or a native draft
statement — as prose-only ingest work (`unstructured`), not as "no captured post
states it". A bare capacity, quant name or speed with no engine/build word beside it
SHALL NOT count as a build claim.

The version token itself MUST be digit-complete and MUST NOT be followed by a
throughput unit (issue #998) or a quant bit-width unit (`bits`, `bits/weight`, `bpw`,
issue #1025). And the claim MUST go through exactly ONE model-aware reader,
`data_gap_analysis.engine_min_claim`: a build-phrase match whose version tokens are
ALL tokens the model's own id/name/full_name spell — a model-version collision like
`glm-5.3-flash` ← "RED-SNOW-5.3-FLASH-MLX-4bit" or `qwen3.8-27b-ps5lm-native` ←
"2-bit Qwen 3.8 27B (PS5LM, llama.cpp port)" — is refused, and a later genuine build
phrase in the same text still claims. The ingest fill (`update_trending.
fill_engine_min_version`) and the gap scan share this reader; `dim_claim` is the ONE
reader accessor `analyse()` and every re-checking consumer use, so a narrowed claim
never reads as a gap on one side and a contradiction on the other (rule 6d).

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

#### Scenario: a model-version collision never claims

- **Given** `glm-5.3-flash` whose only prose is "RED-SNOW-5.3-FLASH-MLX-4bit" and
  `qwen3.8-27b-ps5lm-native` whose only prose is "2-bit Qwen 3.8 27B (PS5LM,
  llama.cpp port)" — the exact rows the gap scan listed as `unstructured:
  engine_min_version` before this change
- **When** the fill or the gap scan runs
- **Then** neither fills a value and neither is classified as prose-only ingest work
  (structuring them would store a model version as an engine build — rule 2)
- **Test:** tests/test_engine_min_version_ingest.py::test_a_model_version_collision_never_fills
- **Test:** tests/test_data_gap_analysis.py::test_a_model_version_is_not_an_engine_build_claim

#### Scenario: a bit-width beside an engine word is not a build version

- **Given** `MLX weights (~7GB), 1.72 bits/weight` and `306.9 tokens/s`
- **When** the build-version token is matched
- **Then** neither matches ("1.7" may not match inside "1.72" — the token is
  digit-complete), while `mlx 0.25.1` still matches
- **Test:** tests/test_engine_min_version_ingest.py::test_bits_per_weight_is_not_a_build

#### Scenario: the fill and the scan share the ONE claim reader

- **Given** `scripts/update_trending.py` and `scripts/data_gap_analysis.py`
- **When** `make test` runs
- **Then** the fill's detector IS `data_gap_analysis.engine_min_claim` (built on the
  ONE `_ENGINE_MIN_TEXT`), `update_trending` carries no second copy of the detector
  vocabulary, and the real-store contradiction guard re-checks through
  `data_gap_analysis.dim_claim` — the same reader `analyse()` used
- **Test:** tests/test_engine_min_version_ingest.py::test_the_build_detector_has_one_implementation
- **Test:** tests/test_data_gap_analysis.py::test_the_real_store_reports_only_figures_it_can_point_at

### Requirement: A storage offload needs a medium and an offload wording

The `storage_offload` free-text detector MUST require a storage medium
(`ssd`/`nvme`/`flash`/`disk`/`hdd`/`storage`) AND an offload/streaming wording in the
same sentence. A `disk` that sits directly after a `<N>GB on ` / `<N>MB on ` size is a
WEIGHT-FILE SIZE, not a medium (issue #1019), and an `offload` word that sits directly
after `layer` / `layers` is a GPU-LAYER offload, not expert streaming — both are
refused at the token.

#### Scenario: a memory offload

- **Given** `"Q4_K_M with 26 MoE layers offloaded to the CPU"`
- **When** the store is analysed
- **Then** the model is NOT reported as naming a storage offload
- **Test:** tests/test_data_gap_analysis.py::test_a_storage_offload_needs_a_medium_and_an_offload

#### Scenario: a file size and a machine's own disk

- **Given** `"4-bit MLX, 2.1GB on disk"` and `"M2 Ultra, 2TB SSD, 192GB unified memory"`
- **When** the store is analysed
- **Then** neither is reported
- **Test:** tests/test_data_gap_analysis.py::test_a_storage_offload_needs_a_medium_and_an_offload

#### Scenario: a genuine storage requirement

- **Given** `"experts streamed from NVMe SSD"` and `"MoE expert offload to SSD"`
- **When** the store is analysed
- **Then** both are reported
- **Test:** tests/test_data_gap_analysis.py::test_a_storage_offload_needs_a_medium_and_an_offload

#### Scenario: a weight-file size plus a layer offload is not a storage requirement

- **Given** `"Unsloth IQ4_XS (~14.6GB on disk), 25 layers offloaded, Q4_0 KV cache"`
  (the sentence #1019 measured on a live row) beside a real
  `"IQ4_XS, experts offloaded to NVMe storage"`
- **When** the store and captures are analysed
- **Then** the first model is NOT in the ingest class — it lands in the acquisition
  class (`not_captured`), which a footprint query may re-ask; the second is reported
- **Test:** tests/test_data_gap_analysis.py::test_a_layer_offload_or_file_size_is_not_a_storage_requirement
