# context-tokens-ingest-traceable

## ADDED Requirements

### Requirement: a captured, correctly-attributed context window is stored on its measurement

A measurement whose source post states the context window it ran with MUST be
able to carry that figure in the contract-declared optional `context_tokens`
key, so a post-backed figure is never left as prose-only when it is correctly
attributed. The structured value MUST be stated by the measurement's own source
post (the `data`-stage source-post readback gate, issue #789) — structuring a
figure a post does not state, or that belongs to a different model, is the
defect this Requirement refuses.

#### Scenario: the shipped rows carry the context their post states

- **Given** the shipped store's `qwen3-8-flash-next-125b` and
  `qwen3-8-flash-next-125b-mtplx-rd1-1` rows, whose shared MTPLX source post
  (Oluwaphilemon1/…/2113748519588635100) states "50 TPS at 200K"
- **When** their `MTPLX` measurements (126.5 t/s) are read
- **Then** each carries `context_tokens: "200K"` — the exact window the post
  states — and `source_post_figure_flags` reports no gated hard-field
  readback contradiction on either row
- **Test:** tests/test_data_gap_analysis.py::test_context_tokens_ingest_traceable_rows_carry_the_post_state
