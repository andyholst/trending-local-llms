# Proposal: data-gap-engine-min-version

Issue: #163

## Why

`make data-gaps` (issue #115) files one issue per changed gap set, and issue
#163 is its top-ranked gap: **`engine_min_version` is absent from the store on
29 of 30 models** (27 of 38 on the store at this revision). `engine_min_version`
is "the engine build or the required flags the figure reproduces on" — a real
requirement dimension, already declared OPTIONAL in *both* contracts
(`data/model_contract.json`, `data/search_contract.json`), so the store **can**
hold it: `"Contract gaps: none"` in the issue body.

The value is not missing from the world — it is missing from the store. The
search captures the post, and the post states the build or the flags
(`data/raw/cpu-20261014-114227.json`: "BigMoeOnEdge on stock llama.cpp (untouched
upstream, submodule)"; `data/raw/amd-20261014-114736.json`: "Vulkan (llama.cpp
b9292), MTP speculative decode"; `data/raw/nvidia-20261014-111628-4.json`:
"-c 57344, -np 4, -b 2048 -ub 2048, -ngl 99, -fa on"), but it lands only in the
post's prose — a measurement's `quant`, the model's `why`, the engine's
registered name — never in the structured field, which is exactly the gap the
analysis reports and the reason it keeps reporting it every refresh.

## What Changes

- **`data/models.json` gains structured `engine_min_version` values** for the
  models whose captured source post **states** a build or the required flags,
  quoting the post's own words. Additive only: no existing key is removed or
  renamed and no existing value is shrunk (`check_no_value_loss` keeps it that
  way). A model whose post states nothing is left unset — an absent field is
  reported as a gap, an invented one is a fabrication.
- **The values are traceable, and it is enforced.** Every model-level
  `engine_min_version` must trace to the model's own captured source text in
  `data/raw/*.json` — the record of the real `…/status/<id>` post — and that is
  now locked by `tests/test_data_gap_analysis.py`:
  `test_engine_min_version_backfill_traces_to_the_captured_source_text`
  asserts the value's wording (every version-like token, and at least one
  distinctive token) is present in the text the search captured for that model,
  and `test_engine_min_version_coverage_can_never_shrink` asserts the dimension
  is carried by a floor of models so the backfill cannot silently regress.
- **The gap is smaller and the ranking says so.** `make data-gaps` moves
  `engine_min_version` off the top of the ranked list. The regression guard for
  that lives in the same test file.

Nothing about the *capability* changes: the contracts already declare the key
OPTIONAL and ingest already merges it onto an existing model
(`update_trending.merge_additive_fields`, `_ADDITIVE_MODEL_FIELDS`); this change
fills the store with the values those two already make representable.

## Impact

`data/models.json` (the backfilled `engine_min_version` values),
`tests/test_data_gap_analysis.py` (two new guards), the OpenSpec change and the
regenerated `OPENSPEC.md` index.

The `tests/test_data_gap_analysis.py` row in `AGENTS.md` §8 (rule 6c: the guard's
row scrolls with the guard) is **review-required, not written here**: `AGENTS.md`
is a protected agent-instruction file and this run has no approver to consent to
the write. The exact replacement row is spelled out in `findings.md`, which is
the working file this run can write.

The generated `README.md` is **byte-identical**: none of the five requirement
dimensions is rendered by `render_readme` (`grep -c engine_min_version
README.md` → 0), so `check_readme_generated` re-renders the same table set from
the store with or without the backfill. No make target, stage, pipeline job,
image or script is added or renamed, so `ARCHITECTURE.md` is unchanged (rule 6h)
— verified by `make architecture-check`.

## Not covered

- The other eight ranked gaps in the same issue (`storage_offload` 26,
  `weight_gb` 26, `context_tokens` 25, `system_ram_min` 22, and the four
  `unstructured:*` entries). They are separate dimensions with separate
  evidence; a value pulled from prose for one of them is a distinct judgement
  and belongs in its own tracked change, not folded into this one (rule 6g —
  analysis files issues, a fix is one issue). `findings.md` records them.
- A *derivation* of `engine_min_version` from the engine registry (e.g.
  "llama.cpp" -> its latest release): the field is "the build the post states",
  and a registry default would be an invented figure.
- Extracting the value automatically at ingest. The four dimensions that are
  free-text-only are deliberately reported as `unstructured` and never as
  captured (AGENTS.md §4); a curated, evidence-carrying backfill is the
  intended closure, and its guard is the traceability test below.
