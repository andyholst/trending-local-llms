# data-backfill

## ADDED Requirements

### Requirement: a structured footprint value is the source post's own statement

Every structured `context_tokens` and `engine_min_version` value on a shipped
model MUST be the model's own captured post text (a real `…/status/<id>` URL),
evidenced by the value's distinctive and numeric tokens appearing in the
`data/raw/*.json` capture for that model. A value no captured post states is a
fabrication (AGENTS.md rule 2) and must not be added; a value flagged by a gap
reader that is only a regex over-match (a throughput figure, a misattributed
post, a benchmark length, a model quant) is reported as a gap, never structured.

#### Scenario: a captured context window is stored for the model that states it

- **Given** the shipped store's `qwen3-8-flash-next-125b` and
  `qwen3-8-flash-next-125b-mtplx-rd1-1` rows, whose capture
  (`Oluwaphilemon1/status/2100499328376713348`) states "50 TPS at 200K context"
- **When** the store is read
- **Then** each row carries `context_tokens: "200000"` (the window the post
  states), evidenced by the captured text and behind a real post
- **Test:** tests/test_data_gap_analysis.py::test_context_tokens_backfill_traces_to_the_captured_source_text

#### Scenario: a captured engine build is stored for the model that states it

- **Given** the shipped `qwen3.8-27b-ps5lm-native` row (capture
  `AGTPinsights/status/2110336928159784961` states "llama.cpp ported natively
  (github.com/cobanov/PS5LM, v0.1, GPL-3.0)") and the `qwen3.8-27b-bonsai-2` row
  (capture states "stock llama.cpp rejects the format so the PrismML fork ran it")
- **When** the store is read
- **Then** `qwen3.8-27b-ps5lm-native` carries `engine_min_version: "llama.cpp
  port (PS5LM)"` and `qwen3.8-27b-bonsai-2` carries `engine_min_version:
  "PrismML llama.cpp fork"`, each evidenced by the model's captured text and
  behind a real post
- **Test:** tests/test_data_gap_analysis.py::test_engine_min_version_backfill_traces_to_the_captured_source_text

#### Scenario: an unsupported footprint value is refused

- **Given** a value naming a token no captured post mentions (a fabricated build
  or window)
- **When** the traceability guard runs
- **Then** the value is not evidenced and the guard fails loudly rather than
  accepting it
- **Test:** tests/test_data_gap_analysis.py::test_context_tokens_backfill_traces_to_the_captured_source_text

### Requirement: the closed footprint dimension cannot silently shrink

The number of models carrying `context_tokens` must never fall below the
shipped floor, and the number the analysis reports missing must not exceed the
filed count plus models added since (issue #472's re-filing lesson) — a backfill
that is later deleted reopens the gap under a gate that notices.

#### Scenario: a removal reopens the gap

- **Given** the shipped store carrying at least the post-backed `context_tokens`
  floor
- **When** a later change removes those values
- **Then** the coverage-floor test fails
- **Test:** tests/test_data_gap_analysis.py::test_context_tokens_coverage_can_never_shrink
