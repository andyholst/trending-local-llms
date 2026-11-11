# cross-model-attribution

## ADDED Requirements

### Requirement: a measurement renders only on the model its source post measured

The shipped store MUST NOT carry, on a model row, a `(engine, tps, hardware,
source_post)` measurement that a different model ID also carries when the source
post measured only one of them.

#### Scenario: a 1B no longer renders a 27B's Mac mini figure

- **Given** the shipped store (`load_store()` of `data/models.json` catalog + `data/measurements.json` + `data/posts.json`)
- **When** the store is scanned for `gemma-3-1b`
- **Then** it has no `MLX` `tps: 18` row whose `source_post` is
  `lightbrd.com/pratikg/status/2108994425166967019`, and no
  `engagement.seen_posts` entry for that post
- **Test:** tests/test_cross_model_attribution.py::test_gemma_3_1b_no_longer_carries_the_27b_figure

#### Scenario: a Gemma 4 26B A4B no longer renders an LFM figure

- **Given** the shipped store (`load_store()` of `data/models.json` catalog + `data/measurements.json` + `data/posts.json`)
- **When** the store is scanned for `gemma-4-26b-a4b`
- **Then** it has no `llama.cpp` `tps: 50.7` row whose `source_post` is
  `lightbrd.com/PaulGugAI/status/2110275665408704970` (the number stays on
  `lfm2.5-24b-a2b`), and no `engagement.seen_posts` entry for that post
- **Test:** tests/test_cross_model_attribution.py::test_gemma_4_26b_a4b_no_longer_carries_lfms_figure

#### Scenario: a qwen3.6-35b-a3b no longer renders a qwen3.8-27b R9700 figure

- **Given** the shipped store (`load_store()` of `data/models.json` catalog + `data/measurements.json` + `data/posts.json`)
- **When** the store is scanned for `qwen3.6-35b-a3b`
- **Then** it has no `llama.cpp` `tps: 51.8` row whose `source_post` is
  `lightbrd.com/xfxjapan/status/2096715285923520644` (the number stays on
  `qwen3.8-27b`), and no `engagement.seen_posts` entry for that post
- **Test:** tests/test_cross_model_attribution.py::test_qwen3_6_35b_a3b_no_longer_carries_qwen3_8_27bs_figure

#### Scenario: the README renders no copied row

- **Given** the shipped `README.md`
- **When** it is rendered from the corrected store as of `generated_utc`
- **Then** Gemma 3 1B has no `MLX` 18 t/s row on the M5 Pro Mac mini, Gemma 4
  26B A4B has no `llama.cpp` 50.7 t/s RTX 3080 row, qwen3.6-35b-a3b has no
  `llama.cpp` 51.8 t/s Radeon R9700 row, and the render is byte-identical to the
  committed file (minus the timestamp line)
- **Test:** tests/test_cross_model_attribution.py::test_the_readme_renders_no_copied_row

### Requirement: the same-post cross-model duplicate scan is reported and the store carries no unallowlisted copy

`make validate` MUST print, on every `data`-stage run, every identical
`(engine, tps, hardware, source_post)` tuple stored on two different model IDs;
and the shipped store MUST NOT contain such a tuple unless it is one of the
documented legitimate allow-list entries (same-family variant IDs or a post that
measured both models).

#### Scenario: the shipped store is clean

- **Given** the shipped store (`load_store()`: catalog + measurements + posts)
- **When** the same-post cross-model duplicate scan runs
- **Then** every identical `(engine, tps, hardware, source_post)` tuple shared by
  two model IDs is in the allow-list, and the three copies this change removes are
  absent
- **Test:** tests/test_cross_model_attribution.py::test_the_same_post_cross_model_scan_is_clean

#### Scenario: a regression is reported, never silent

- **Given** a store where a second model ID carries a copied tuple again
- **When** the validator data stage runs
- **Then** the scan names the tuple and the two model IDs as a WARN and the run
  still exits 0 (same pattern as the duplicate-run scan, issue #459)
- **Test:** tests/test_cross_model_attribution.py::test_a_regression_is_reported_never_silent

### Requirement: the scan is wired into a stage CI runs

The check MUST be registered under the `data` stage, and that stage MUST be
selected by a make target (rule 6d).

#### Scenario: the registration is read

- **Given** `scripts/validate.py` and the `Makefile`
- **When** the guard reads them
- **Then** `check_cross_model_attribution` is registered under `data` and
  `validate.py --only data,removal` exists
- **Test:** tests/test_cross_model_attribution.py::test_the_check_is_wired_into_the_data_stage
