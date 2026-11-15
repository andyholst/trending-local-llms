# data-gap-analysis

## MODIFIED Requirements

### Requirement: The context_tokens detector states a window, not a benchmark point

The data-gap analysis SHALL classify a model whose captured post states a single
context window in free text — `80k context`, `256K context window`, `32K ctx`,
`context size 131072` — as prose-only ingest work (`unstructured`), and SHALL classify
a model whose captured post states no window figure at all as an acquisition gap
(`missing`).

The claim MUST go through exactly ONE model-aware reader,
`data_gap_analysis.context_tokens_claim`, reached through the shared `dim_claim`
accessor (rule 6d). A `_CTX_TEXT` match whose figure is one of the throughput-qualified
context points of a MULTI-POINT sweep segment — a `;`/newline/sentence-dot segment
carrying two or more context sizes within reach of a `t/s`/`tok/s`/`TPS` reading, like
`0K context (21.11 t/s at 32K, 21.58 at 8K)` or `61 TPS at 100K context, 50 TPS at
200K` — MUST be refused: a sweep states no single window, so the model belongs in
`missing`, not in an ingest class. A figure that is itself a throughput reading
(`21.11` before `t/s`, `21.58` before `at 8K`) MUST NOT count as a sweep size. A
window stated apart from a sweep MUST still claim even when the same text also sweeps,
and a LONE benchmark point MUST stay claimable (only multi-point sweeps are refused).
A sentence boundary MUST NOT split a decimal: `.` ends a segment only when whitespace
follows it.

#### Scenario: the dflash2-style sweep is an acquisition gap, not an ingest job

- **Given** a store model with no structured `context_tokens` whose captured quant
  reads `UD-Q4_K_XL target + DFlash2 drafter; n=4; 0K context (21.11 t/s at 32K,
  21.58 at 8K)`
- **When** `analyse` runs over the store and the raw captures
- **Then** the model is in `missing:context_tokens` and not in
  `unstructured:context_tokens`
- **Test:** tests/test_data_gap_analysis.py::test_a_benchmark_sweep_states_no_context_window

#### Scenario: the MTPLX multi-point capture states no window either

- **Given** a captured measurement whose `why` reads `peak 126.5 TPS, 61 TPS at 100K
  context, 50 TPS at 200K` on a model with no structured `context_tokens`
- **When** `analyse` runs
- **Then** the model is in `missing:context_tokens` and not in
  `unstructured:context_tokens`
- **Test:** tests/test_data_gap_analysis.py::test_a_benchmark_sweep_states_no_context_window

#### Scenario: a stated window — even beside a sweep — still claims

- **Given** two captured models, one reading `runs 80k context steady on the 24GB
  card` and one reading `It ships a 256K context window; peak 61 TPS at 100K, 50 TPS
  at 200K`
- **When** `analyse` runs
- **Then** both models are in `unstructured:context_tokens` (the sweep points refused,
  the stated windows claimed)
- **Test:** tests/test_data_gap_analysis.py::test_a_benchmark_sweep_states_no_context_window

#### Scenario: the shipped store's prose claims are exactly the stated windows

- **Given** the shipped `data/models.json` and the captured `data/raw/*.json`
- **When** `analyse` runs over them
- **Then** `unstructured:context_tokens` is exactly `{qwen-3.6-27b}` and
  `qwen3.8-27b-strix-halo-dflash2` appears in `missing:context_tokens`
- **Test:** tests/test_data_gap_analysis.py::test_the_real_store_reports_only_figures_it_can_point_at
