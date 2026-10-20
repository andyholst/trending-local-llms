# data-gap-reporting

## ADDED Requirements

### Requirement: An unstructured claim names a figure the model itself states

The data-gap analysis MUST report a dimension as `unstructured` only when the
model's OWN text (its `quant` / `hardware` / `why`, or the same fields on one of
its measurements) states a FIGURE for that dimension. A word that merely names
the topic — `context`, `context lookup`, `kv-cache`, `Flash Attention` — is not a
figure, and a property of the engine (its registry note) is not evidence about a
model that uses it.

WHEN the analysis decides that a model "names the value only in free text",
THEN every field is scanned on its own, the engine registry's notes are never
scanned, and the match is a figure rather than a keyword.

#### Scenario: an engine's registry note is not per-model prose

- **Given** a model whose only context wording lives in the note of the engine it names (`DFlash2` — "Speculative decoding + context-lookup")
- **When** the store is analysed
- **Then** the model is NOT reported as `unstructured:context_tokens`
- **Test:** `tests/test_data_gap_analysis.py::test_an_engine_note_is_not_per_model_prose_evidence`

#### Scenario: a context window needs a figure

- **Given** measurements whose text reads `kv-cache q4_0`, `DFlash2 + context lookup, 25K-token document reproduction` and `30 tok/s`
- **When** the store is analysed
- **Then** none of them is reported as a prose context window, while `80k context`, `256K ctx.` and `262,144-token context` are
- **Test:** `tests/test_data_gap_analysis.py::test_a_context_window_needs_a_figure`

#### Scenario: Flash Attention is not a storage medium

- **Given** a measurement whose quant reads `llama-server with GPU offload, Flash Attention, 262,144-token context`
- **When** the store is analysed
- **Then** it is NOT reported as `unstructured:storage_offload`, while `experts streamed from NVMe SSD` still is
- **Test:** `tests/test_data_gap_analysis.py::test_flash_attention_is_not_a_storage_medium`

#### Scenario: a VRAM capacity is not a weights figure

- **Given** a measurement whose quant reads `MXFP4-engram GGUF, 32K context at fp16, 16GB on VRAM + 60GB RAM`
- **When** the store is analysed
- **Then** it is NOT reported as `unstructured:weight_gb`, while `Q4_K_M (16.8GB weights)` and `<20GB weights` still are
- **Test:** `tests/test_data_gap_analysis.py::test_a_vram_capacity_is_not_a_weights_figure_even_beside_gguf`

### Requirement: The real store's remaining prose claims are figures

On the store this change ships against, the `unstructured:*` set MUST contain only
models whose own text states the figure, and the run MUST record the measured
before/after so a future regression is visible (6 -> 2 `context_tokens`, 3 -> 2
`weight_gb`, 1 -> 0 `storage_offload`). The `missing:*` coverage counts MUST be
unaffected: they are real acquisition gaps, not a reporting artefact.

WHEN the analysis runs over `data/models.json`,
THEN each `unstructured` claim can be pointed at a figure in that model's own text,
and the structured-coverage counts still report every model that has no value.

#### Scenario: the shipped store reports only real figures

- **Given** the real `data/models.json` and the real contracts
- **When** `analyse()` runs
- **Then** every `unstructured` entry's text matches a figure pattern, the claims are at most the measured set, and `missing` still names the models with no structured value
- **Test:** `tests/test_data_gap_analysis.py::test_the_real_store_reports_only_figures_it_can_point_at`
