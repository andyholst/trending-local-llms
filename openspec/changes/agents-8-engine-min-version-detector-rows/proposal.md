# The §8 rows the #1020 engine-build detector owed are WRITTEN

**Issue:** [#1128](https://github.com/andyholst/trending-local-llms/issues/1128)
**Capability:** `agents-guard-registry`

## Why

Issue #1020 (fixed by PR #1127) found that `engine_min_version` was being mined from sentences
that name an **engine** beside a **throughput figure** — `"same post: llama.cpp 306.9 tokens/s"`
(`qwen2.5-0.5b`), `"llama.cpp 44.8 tokens/s"` (`gemma-4-e4b`), a comparison whose rate sits on
the engine side (`"345.9 vs llama.cpp's 306.9 tokens/s"`), a toolchain compound
(`"SonicBoom 0.0.3 (C++/CUDA …"`), and quant/model-name prose (`"ternary MLX weights"`,
`"PS5LM, llama.cpp port"`, `"TensorFold vs vLLM"`, `"ExLlamaV3 + Hermes Agent"`). `_ENGINE_MIN_TEXT`
read all of them as build claims, so the analysis filed **seven models** as `engine_min_version`
ingest work the chain could not fill honestly (rule 2: structuring one stores a speed or a name
as a build requirement). PR #1127 shipped the refusal — two guards in
`tests/test_engine_min_version_ingest.py` and one in `tests/test_data_gap_analysis.py` — green in
`make test`, **with no row in AGENTS.md §8**.

`grep -n "test_bare_engine_names" AGENTS.md` on the base names nothing (measured on
`origin/master`): the rulebook that is supposed to be the map of *which guard catches which drift
class* cannot tell a reader that the throughput-adjacency refusal exists at all. That is exactly
the defect rule 6c + the `agents-guard-registry` capability (#310/#369/#1087, the
`owed-guard-rows-landed` change) exist to close, and it is why #1128 declared its owed row with
the full text in its own body (`- **Owed-row:** <!-- owed-row: section=8
needle=tests/test_engine_min_version_ingest.py -->`).

## What Changes

- **`AGENTS.md` §8** gains one row naming both modules and all three guards
  (`test_bare_engine_names_beside_throughput_figures_never_claim`,
  `test_explicit_build_phrases_still_claim`,
  `test_engine_min_version_candidates_are_engine_names_not_build_claims`), describing the drift
  class and citing #1020 / PR #1127. It sits beside the existing `engine_min_version` rows
  (#163, #214, #1017, #1025/#1019) so a reader tracing the dimension finds it.
- **`tests/test_agents_rows.py`** gains the pin
  `test_the_engine_min_version_bare_engine_name_row_is_written` (rule 6c): the row must be
  present, name both modules, cite the issue and the PR, state the drift class, and the three
  guards must be real functions of the modules the row names — so a rename or deletion turns the
  pin RED instead of leaving a row that describes nothing.
- No rule text changes anywhere else in `AGENTS.md`, so rule 3c's disclosure is #1128's own
  owed-row declaration (§8 only); no `make` target, script, pipeline job or image moves, so
  `ARCHITECTURE.md` and `make architecture-check`'s mechanical half are untouched (verified).

## Impact

- **Capability:** `agents-guard-registry` (one added requirement).
- **Affected code:** `AGENTS.md` §8, `tests/test_agents_rows.py`.
- **Data:** none — `data/models.json`, `data/raw/*` and the contracts are byte-identical (rule 3b).
- **Not covered:** the *content* of #1020's fix (already merged as PR #1127), the separate
  `engine_min_version` compound-value question raised by #1129, and the acquisition half (a real
  post that states a minimum build) which #878/#883 still own. This change lands the rulebook row
  and the pin that keeps it honest — nothing else.
