# bare-param-size-figure-refusal (issue #1018)

Issue: #1018
PR: #1131
Related: #456/#468/#650/#651/#652 (the named-model attribution chain)

## Why

Issue #1018 filed a stored figure that cannot belong to the row it sits on: a
`qwen3.6-27b` llama.cpp measurement whose captured text reads
`Q4_K_M (16.8GB weights), + flash-attention + kv-cache q4_0; 30 tok/s at 70B Q4`
(`data/raw/metal-20261014-210435.json`, two such sentences). The run named in the
post is at a **70B parameter size**; the row is 27B.

The attribution seam (`scripts/update_trending.py::misattributed_measurement_reason`,
issue #468) proves a mix-up from a **family-named** mention — family + version +
parameter size (`named_models_in_text`). This sentence names **no model at all**, only a
size, so the seam saw nothing and the measurement landed clean. Measured over the shipped
`data/raw/*.json`: the #468 seam refuses 5 captures; the same sweep with a second proof
refuses 7 — the two extra ones are exactly the #1018 sentences, and no other capture
changes state. So the gap is not "a rule that fires wrongly", it is a class the pipeline
cannot see: a throughput figure whose model is implied by a bare parameter size.

## What Changes

- `scripts/update_trending.py` gains the second proof beside the named-model one:
  `_BARE_PARAM_SIZE_RE` + `bare_param_sizes_in_text()` +
  `bare_param_size_figure_reason()`. A size counts as bare only when it stands alone (a
  lookbehind refuses the `B` inside `A2B` / `LFM2.5-24B-A2B`) and sits in a
  quant/throughput phrase (`at 70B Q4`, `70B dense`, `70B model`), so `16.8GB weights`,
  `256GB` memory and `1.58TB/s` are never read as a model size.
- `misattributed_measurement_reason` asks the new proof when no family-named mention
  exists, reusing the SAME rescues it already has: a comparison cue with exactly one t/s
  figure is a JOINT figure (issue #651), a cue with several figures is a per-model
  bake-off, a text that names the row's own model too is a multi-model post, a size equal
  to the row's own is the row's own figure, and a row's `measurement_model_aliases`
  (issue #652) documents a real exception. ONE implementation (rule 6d): the ingest
  refusal and the validator's report both reach it through this seam, so no second copy
  of the rule can drift.
- No data change: nothing is removed from `data/models.json`, `data/raw/*.json` or
  `data/refusals.json` (rule 3b). The shipped 70B sentences stay in the raw capture; the
  next refresh refuses them at ingest and records them in the refusal ledger, and
  `scripts/data_gap_analysis.py` stops crediting a refused capture's prose.
- `tests/test_measurement_attribution.py` gains six tests, including one that runs the
  seam against the shipped `data/raw/metal-20261014-210435.json` (real data, no fixture).

## Impact

- **Capability:** `measurement-attribution` (one ADDED Requirement, five scenarios).
- **Code:** `scripts/update_trending.py` (one seam), `tests/test_measurement_attribution.py`.
- **CI:** unchanged paths — the seam is called by the existing ingest wiring and the
  existing `validate` data stage; `make test` runs the new tests. No new `make` target
  (rule 6d/6m).
- **Data:** additive only. Existing rows and values are untouched; the guard changes what
  a FUTURE ingest may file.
- **Not covered:** the owner's ruling on which row the shipped 70B figure belongs to
  (issue #1018's and #650's Done-when, rule 3b) is NOT decided here — no row is removed,
  renamed or re-homed. A genuine re-attribution is a human act, and the refusal reason
  names `measurement_model_aliases` as the data key that records it.
