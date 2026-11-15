# Proposal: data-gap-context-tokens-capture

Issue: #994 — `data-gap: context_tokens (69 models)`
PR: #1004

## Why

`make data-gaps` (issue #115) files ONE issue per changed gap set, and issue #994
is that report. Its ranked gaps are dominated by ACQUISITION work — a figure no
captured post states, so only a new search can close it — and UNTRACEABLE figures
(store prose with no post behind it, a capture job). Neither is this change's
scope: this leg does not run searches.

The implementable portion of the issue is its **"stated in prose only (ingest
job)"** class: models whose captured source post genuinely states the figure and
the store lacks it as a structured key. The contracts already declare every such
dimension OPTIONAL on a model and on a measurement (`data/model_contract.json`,
`data/search_contract.json`; "Contract gaps: none" in the issue body), so closing
them is a data edit, not a schema change. This is the exact shape of the precedent
backfills #163 (`engine_min_version`) and #364 (`storage_offload`).

Measured on the store (this change is the verification): among the ingestion-flagged
models, only FOUR carry a value a captured post really states at the right type.
The rest are detector over-matches — throughput figures read as versions, a
misattributed post, a benchmark context length — and structuring them would
fabricate (AGENTS.md rule 2), so they are left as gaps and reported.

## What Changes

- **`data/models.json` gains four structured values**, each traceable to the
  model's own captured post text and a real `…/status/<id>` URL (additive only,
  rule 3b — no key removed, no value shrunk):
  - `context_tokens: "200000"` on `qwen3-8-flash-next-125b` and
    `qwen3-8-flash-next-125b-mtplx-rd1-1` — post
    `Oluwaphilemon1/status/2100499328376713348` states "50 TPS at 200K context".
  - `engine_min_version: "llama.cpp port (PS5LM)"` on `qwen3.8-27b-ps5lm-native` —
    post `AGTPinsights/status/2110336928159784961` states "llama.cpp ported
    natively (github.com/cobanov/PS5LM, v0.1, GPL-3.0)".
  - `engine_min_version: "PrismML llama.cpp fork"` on `qwen3.8-27b-bonsai-2` —
    post `Oluwaphilemon1/status/2105846759754788886` (captured phrase "stock
    llama.cpp rejects the format so the PrismML fork ran it").
- **`tests/test_data_gap_analysis.py` gains a `context_tokens` backfill guard**
  mirroring the engine_min_version (#163) and storage_offload (#364) ones:
  every structured `context_tokens` value must be evidenced by the model's
  captured source text (distinctive + numeric token present) and sit behind a
  real post, and the dimension's coverage cannot silently shrink. The two new
  `engine_min_version` values are already covered by the existing #163 test.

## Impact

- `make data-gaps` reports two fewer `unstructured:context_tokens` / two fewer
  `unstructured:engine_min_version` models. The bulk of #994's ranked gaps (the
  acquisition and untraceable classes) is unchanged and remains owned by future
  searches — closure of this issue is the ingest portion, not the whole report.
- No ingest, README, contract or workflow behaviour changes beyond the regenerated
  README card-fit / engine cells for the four models.

## Not covered

- Acquisition gaps ("not stated by any captured post") — only a new read.
- Untraceable figures ("stated in prose only, no post behind it", issue #470) —
  a capture job, and structuring one would invent the attribution.
- Engine-min-version flags on `qwen2.5-0.5b` / `gemma-4-e4b` (the captured value
  is throughput, "llama.cpp 306.9 tokens/s"), `glm-5.3-flash` / `minicpm-v-4.7` /
  `bonsai-2-27b-mac-m4-max` (the flag is a model quant or bits-per-weight, not an
  engine build); `context_tokens` on `qwen-3.6-27b` (misattributed, names Qwen
  3.5 35B) and `qwen3.8-27b-strix-halo-dflash2` (a benchmark length, not a
  window); `weight_gb` on `qwen3.6-27b` (the captured figure sits under sibling
  `qwen3.6-35b-a3b` and names "70B Q4"); `storage_offload` on `qwen3.8-27b`
  ("on disk, N layers offloaded" is a weight/layer footprint, not expert
  streaming). Each is reported, never fabricated.
