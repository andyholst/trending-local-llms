## ADDED Requirements

### Requirement: A parameter size stated with no model named is a refusal too

At ingest, a measurement whose `quant` or `why` text states a figure at a parameter size
that is NOT the row's own size, with no model named in the phrase, MUST be refused,
loudly, with the source post named. A size counts as stated only when it stands alone
(a `B` inside a model token such as `A2B` or `LFM2.5-24B-A2B` is not a size) and sits in a
quant or throughput phrase (`at 70B Q4`, `70B dense`, `70B model`), so a memory size
(`256GB`), a bandwidth (`1.58TB/s`) or a weight size (`16.8GB weights`) is never read as a
model size. The rescues of the named-model proof apply unchanged: a comparison cue with
exactly one t/s figure is a JOINT figure, a cue with several figures is a per-model
bake-off, a text naming the row's own model too is a multi-model post, a size equal to the
row's own is the row's own figure, and `measurement_model_aliases` documents the exception.

#### Scenario: the measured defect

- **Given** a row `Qwen 3.6 27B` and a measurement whose `quant` reads "Q4_K_M (16.8GB
  weights), + flash-attention + kv-cache q4_0; 30 tok/s at 70B Q4"
- **When** `refuse_misattributed_measurements` is called on that row
- **Then** the measurement is refused, the reason names `70b` and `27b`, offers
  `measurement_model_aliases` as the data key, and carries the source post
- **Test:** tests/test_measurement_attribution.py::test_a_bare_parameter_size_figure_is_refused

#### Scenario: the shipped capture that defines issue #1018

- **Given** `data/raw/metal-20261014-210435.json` and the shipped `data/models.json`
- **When** `refuse_misattributed_measurements` runs on its `qwen3.6-27b` row
- **Then** both `70B` sentences are refused with real status URLs and the row's other
  measurements are kept untouched
- **Test:** tests/test_measurement_attribution.py::test_the_shipped_capture_that_defines_issue_1018_is_refused

#### Scenario: the row's own size stated bare

- **Given** a row `Qwen 3.6 27B` and a measurement reading "128K context at 27B Q4;
  28.99 t/s"
- **When** the refusal check runs
- **Then** the measurement is kept (a bare size that IS the row's size is the row's figure)
- **Test:** tests/test_measurement_attribution.py::test_a_bare_size_that_is_the_row_own_size_is_kept

#### Scenario: a size inside a model token, and a hardware size

- **Given** a row `Qwen 3.6 27B` and measurements reading "the 24B A2B MoE variant ran at
  40 t/s", "LFM2.5-24B-A2B served by vLLM" and "on a 256GB unified-memory box; 1.58TB/s"
- **When** the refusal check runs
- **Then** all are kept (an active-parameter token, a model name and a memory/bandwidth
  figure are not foreign model sizes)
- **Test:** tests/test_measurement_attribution.py::test_a_size_inside_a_model_token_is_not_a_bare_size
  and tests/test_measurement_attribution.py::test_a_memory_or_bandwidth_figure_is_not_a_param_size

#### Scenario: the named proof's rescues are the same rescues

- **Given** a `Qwen 3.6 27B` row with (a) a post naming this row and a `125B model`, (b) a
  bake-off sentence with one figure per model, (c) a `27B vs 70B` comparison carrying ONE
  t/s figure
- **When** the refusal check runs
- **Then** (a) and (b) are kept and (c) is refused as a JOINT figure
- **Test:** tests/test_measurement_attribution.py::test_the_bare_size_rescues_match_the_named_ones
