# Proposal: engine-min-version-phrasings

Issue: #214
PR: #876

## Why

`data_gap_analysis.py` classifies a missing dimension by scanning free text, but the
`engine_min_version` detector matches only `\bflag\b|n[-_]gpu[-_]layers|--\w`. The
phrases posts actually use to state a build — `BigMoeOnEdge on stock llama.cpp
(untouched upstream, submodule)`, `MLX 4-bit Swift 1.5 adapter`, `Q4_0 KV cache,
native MTP draft` (measured in `data/raw/cpu-20261014-114227.json` and
`data/raw/metal-20261014-210311.json`) — match nothing, so the analysis reports
`unstructured:engine_min_version` as empty and the acquisition/ingest split cannot
tell a stated-but-unstructured figure from one no post states. That is what made
issue #163's headline gap look unactionable (issue #214).

## What Changes

- Widen the `engine_min_version` dimension's `text` pattern (additively, keeping the
  old flag/-ngl/--x alternatives) to also match, per field and never across joined
  fields (#456's rule):
  - an engine name (`llama.cpp`, `ollama`, `vllm`, `mlx`, `cuda`, …) beside a version
    number;
  - a llama.cpp `b<NNNN>` build tag beside the engine name;
  - provenance words: `untouched upstream`, `stock llama.cpp`, `from source`,
    `nightly build`, `main branch`, `submodule`, `commit <hex>`;
  - a version beside an `adapter`/`fork` name;
  - a `q4_0`-class KV-cache quant type beside a `kv cache`/`cache type` word, and
    `native … draft` — the build requirements #214's captures state.
- A test (rule 6c) that fails on the old regex and locks both directions: #214's
  phrases classify as `unstructured:engine_min_version` (an ingest job), while bare
  capacities and quant names stay NOT a build claim (#213's false-positive class).

## Impact

- `scripts/data_gap_analysis.py` — the ONE detector; `make data-gaps`,
  `make data-gap-issue` and `check_untraceable_figures` all read it (rule 6d).
- `tests/test_data_gap_analysis.py` — new failing-on-old-code test.
- No contract, data or README-template change; additive only (rule 3b).

## Not covered

- No ingest backfill of `engine_min_version` values (that is ingest work #163 owns);
  this change only makes the analysis SEE the statements, per #214's Done-when.
