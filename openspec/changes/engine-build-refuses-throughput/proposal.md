# Proposal: engine-build-refuses-throughput

Issue: #1006 — "The gap reader over-matches throughput as `engine_min_version`"

## Why

`_ENGINE_MIN_TEXT` (`scripts/data_gap_analysis.py`) decides whether a captured
post (or the store's own prose) *states an engine build*, and that flips the
model between an **acquisition** gap ("no captured post states a figure — a new
search is the fix") and an **ingest** gap ("stated in prose only — an ingest
job"). The `engine → <version>` branch matched any `\d+\.\d+` within 24 chars
of an engine name, so a **t/s speed** read as a build version: the captured
"llama.cpp 306.9 tokens/s on the identical GGUF" and "llama.cpp 44.8 tokens/s"
surfaced `qwen2.5-0.5b` and `gemma-4-e4b` as *stated in prose only, an ingest
job*. Structuring them would store a **speed** as an `engine_min_version` — a
rule 2 fabrication. The statement is a speed, not a build; the correct class is
the acquisition gap a re-search can close.

## What Changes

`_ENGINE_MIN_TEXT` refuses a `<version>` that is **immediately followed by a
throughput unit** (`tokens/s` / `tok/s` / `TPS`), applied at the version token
itself so every engine→version and version→engine branch (and the adapter/fork
branches) stops matching a rate as a build. A genuine build phrase — e.g.
`llama.cpp build 2.1, measured 306.9 tokens/s`, where the version precedes a
later, separate speed — still matches, because the lookahead only bites when the
very next word is a rate. The two affected rows reclassify from
`unstructured:engine_min_version` to the acquisition bucket.

## Not covered

Only the **throughput-after-version** overmatch this issue names. A *different*
sibling where the number beside an engine is a **model version** or a
**bit-width** (e.g. GLM-5.3-Flash's `5.3`, Qwen 3.8 `27B (PS5LM, llama.cpp port)`,
`1.72 bits/weight`) is a separate overmatch with separate evidence and praise
criteria; it is filed as a finding (rule 6g), not widened into this change.

## Impact

A few models move from the `unstructured:engine_min_version` ingest bucket to
the `not_captured` acquisition bucket in the data-gap report and the filed issue
— a correct reclassification, never removal of a value (rule 3b). No data, no
contract, no README changes. The engine-build detection stays as precise as
before for genuine build phrasings (#214, #213).
