# Engine-build claims no post supports are declared unverified on the model row

**Issue:** [#883](https://github.com/andyholst/trending-local-llms/issues/883)
PR: #1101
**Capability:** `data-gap-analysis`

## Why

Five ranked rows state an engine **build** in free text that no captured post supports —
the Yukon Research `mlx.fast` optimization-challenge build (`bonsai-2-9b-apple-silicon-yukon`),
the SonicBoom benchmark baseline behind `qwen2.5-0.5b`'s 345.9-vs-306.9 t/s, the
`mlx-serve 26.10.1` / TensorFold / oMLX distillation on `qwen3-8-flash-next-125b`,
`SonicBoom 0.0.3 (C++/CUDA, MLIR, zero Python)` on `gemma-4-e4b`, and `vLLM 0.28 on native
Windows with ROCm 7.15` on the r9700 row `qwen3.8-27b-r9700-vllm-dflash2-w4a16`. The analysis
flagged them `stated_untraceable` (rule 2, issue #470), and the #163 backfill guard refuses to
structure them because **no capture evidences them** — so each claim stayed unattributable
prose inside `why`, invisible to the footprint query that is supposed to re-ask it. Issue #883
names two ways to close it: capture the post that records the build, **or** report the prose
as unverified on the model row. This change lands the second, deterministic half honestly.

## What Changes

- The five flagged rows gain a model-level `engine_min_version` distilled from the row's own
  text and carrying the canonical `(est)` marker (rule 2) — a declared estimate, attributable
  to the row, and listed by `declared_estimate.footprint_estimates()` as re-askable by the
  derived footprint query. Additive only (rule 3b): a key is added to five models; no value
  is removed or shrunk.
- `tests/test_data_gap_analysis.py::test_engine_min_version_backfill_traces_to_the_captured_source_text`
  exempts a **marked** estimate from the evidence and post-URL checks (a `(est)` value claims
  no fact — that is what rule 2 permits) while an **unmarked** invented value stays fully
  gated; the boundary is pinned by two new checks.
- New shipped-store guard `test_untraceable_engine_build_prose_is_declared_unverified_in_the_store`:
  the untraceable `engine_min_version` class is empty on the shipped store, the five rows
  carry marked values, and the report names them as declared estimates.

## Impact

- Capability: `data-gap-analysis` (report semantics unchanged; the class empties on real data)
- Affected: `data/models.json` (five added keys), `tests/test_data_gap_analysis.py`
- **NOT covered:** the acquisition half of #883/#878 stays open — only a future capture of a
  post that actually records the Yukon `mlx.fast` challenge build, SonicBoom 0.0.3 or the
  vLLM 0.28-on-Windows-ROCm-7.15 figure retires these estimates. They are re-asked by every
  footprint query (`<id> vram ram context weights offload engine version`) meanwhile; an
  unmarked value may still never enter the store.
