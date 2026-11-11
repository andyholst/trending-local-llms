# Proposal: data-gap-storage-offload

Issue: #364 — `data-gap: storage_offload (41 models)`

## Why

`make data-gaps` (issue #115) files ONE issue per changed gap set, and issue
#364 is its top-ranked gap: **`storage_offload` is absent from the store on 39 of
47 models** (41 of 49 on the store the issue was filed from). `storage_offload`
is "the storage a run streams experts / weights from" — a real requirement
dimension, already declared OPTIONAL in *both* contracts
(`data/model_contract.json`, `data/search_contract.json`) on the model **and** on
a measurement, so the store **can** hold it: `"Contract gaps: none"` in the issue
body. This is the same shape as issue #163 (`engine_min_version`), whose
implemented change (`openspec/changes/data-gap-engine-min-version`) sits in this
tree as the precedent.

The value is not missing from the world — it is missing from the store. The
search captures the post, and the post states the offload — but it lands only in
the post's prose (a measurement's `quant`, the measurement's `hardware`) and never
in the structured field. Measured on the real store: `deepseek-v4.1-flash` is
recorded as running on

    hardware: "RTX A4500 16GB VRAM + 128GB DDR5, 192GB engram on Gen4 7GB/s NVMe
               (MoE experts streamed from SSD to CPU)"
    quant:    "MXFP4 GGUF, full precision; custom llama.cpp build
               (hikicoder/llama.cpp branch dsv41-ada-medvram), --moe-stream
               SSD-streamed experts, heat-throttled"

— a real `…/status/<id>` post (`HikiCoder/status/2103043114277486893`, 2 likes /
3 comments / 252 views) that states storage offload outright, while the model
carries **no** `storage_offload`. That is exactly the gap the analysis reports
and the reason it keeps reporting it every refresh.

## What Changes

- **`data/models.json` gains a structured `storage_offload`** for the models
  whose captured source post **states** storage offload, quoting the post's own
  words. Additive only: no existing key is removed or renamed and no existing
  value is shrunk (`check_no_value_loss` keeps it that way). A model whose post
  states nothing is left unset — an absent field is reported as a gap, an
  invented one is a fabrication.
- **The value is traceable, and it is enforced.** Every model-level
  `storage_offload` must trace to the model's own captured source text in
  `data/raw/*.json` — the record of the real `…/status/<id>` post — locked by
  `tests/test_data_gap_analysis.py`:
  `test_storage_offload_backfill_traces_to_the_captured_source_text` asserts each
  value's storage tokens (a media word such as `ssd` / `nvme` / `flash` / `disk`,
  and every size/capacity token) are present in the text the search captured for
  that model, and `test_storage_offload_coverage_can_never_shrink` asserts the
  dimension is carried by a floor of models so the backfill cannot silently
  regress.
- **The gap is smaller and the ranking says so.** `make data-gaps` reports fewer
  models missing `storage_offload` than the 41/49 the filed issue recorded. The
  regression guard for that lives in the same test file.

Nothing about the *capability* changes: the contracts already declare the key
OPTIONAL and ingest already merges it onto an existing model
(`update_trending.merge_additive_fields`, `_ADDITIVE_MODEL_FIELDS`); this change
fills the store with the values those two already make representable.

## Impact

`data/models.json` (the backfilled `storage_offload`), `tests/test_data_gap_analysis.py`
(two new guards, wired into its `main()`), the OpenSpec change and the regenerated
`OPENSPEC.md` index.

The generated `README.md` is **byte-identical**: `storage_offload` is not rendered
by `render_readme` (`grep -c storage_offload README.md` → 0), so
`check_readme_generated` re-renders the same table set from the store with or
without the backfill. No make target, stage, pipeline job, image or script is
added or renamed, so `ARCHITECTURE.md` is unchanged (rule 6h) — verified by
`make architecture-check`.

## Not covered

- The other eight ranked gaps in the same issue (`context_tokens` 30,
  `weight_gb` 27, `unstructured:weight_gb` 23, `engine_min_version` 20,
  `system_ram_min` 20, `unstructured:storage_offload` 8,
  `unstructured:context_tokens` 4, `unstructured:system_ram_min` 1). They are
  separate dimensions with separate evidence; a value pulled from prose for one
  of them is a distinct judgement and belongs in its own tracked change, not
  folded into this one (rule 6g — analysis files issues, a fix is one issue).
  `findings.md` records them.
- **Backfilling `storage_offload` for a model whose captured text does not state
  it.** Most of the 39 missing models are dense (or run fully in VRAM/RAM) and
  have no storage offload to record; only one — `deepseek-v4.1-flash` — has a
  captured post that states it. Inventing a value for the rest would be the one
  failure this stage must never make.
- **Deriving the offload from the engine registry** (e.g. "Strata" ⇒ "experts on
  SSD"): the field is "the offload the post states", and a registry default would
  be an invented figure.
- A *derivation* of the value at ingest from free text. The dimensions that are
  free-text-only are deliberately reported as `unstructured` and never as
  captured (AGENTS.md §4); a curated, evidence-carrying backfill is the intended
  closure, and its guard is the traceability test below.
