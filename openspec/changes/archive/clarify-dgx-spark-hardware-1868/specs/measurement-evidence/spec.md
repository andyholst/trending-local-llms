## ADDED Requirements

### Requirement: The two qwen3.6-35b-a3b hardware values carry an additive DGX-Spark clarification

`data/measurements.json` SHALL keep the exact string `Radeon 8060S / Strix Halo 128GB (ASUS Ascent GX10, GB10)` as a byte-for-byte leading substring of the `hardware` value on the `qwen3.6-35b-a3b` / Ollama / 87.2 row and the `qwen3.6-35b-a3b` / Magnitude / 188.9 row. Each value SHALL have appended text that names the NVIDIA DGX Spark (GB10) as the machine that produced the figure and cites the sibling post `niklaslenz_ai/status/2111204284453044383` together with its `NVIDIA DGX Spark (one)` label. This SHALL be an append only: no other key or value in either row, anywhere else in `data/measurements.json`, or in `data/models.json` / `data/posts.json` SHALL change.

#### Scenario: Both rows preserve the original hardware text verbatim and append the clarification

- **Given** the real shipped `data/measurements.json` with the two `qwen3.6-35b-a3b` rows named in #1868
- **When** the real-file guard reads each row's `hardware` value
- **Then** the original string is present as a leading substring, the value names `NVIDIA DGX Spark (GB10)`, cites `niklaslenz_ai/status/2111204284453044383` and `NVIDIA DGX Spark (one)`, and no stored value was replaced or removed
- **Test:** tests/test_dgx_spark_hardware_clarification_1868.py::test_original_hardware_text_preserved_verbatim

#### Scenario: The clarification is additive and cites the sibling evidence

- **Given** the same two real rows
- **When** the guard inspects the appended text
- **Then** the original text is a leading substring (append-only), the NVIDIA DGX Spark (GB10) is named, and both the sibling post and its `NVIDIA DGX Spark (one)` label are cited
- **Test:** tests/test_dgx_spark_hardware_clarification_1868.py::test_clarification_is_additive_and_names_dgx_spark

#### Scenario: No other measurement value changed anywhere in the store

- **Given** the whole real measurements store with only these two `hardware` fields normalised to a placeholder
- **When** the guard computes a canonical digest and compares it to the digest pinned from base `3c00bf44`
- **Then** the digests are equal, exactly two fields were normalised, and the sibling store files `models.json` and `posts.json` are byte-identical to base
- **Test:** tests/test_dgx_spark_hardware_clarification_1868.py::test_no_other_measurement_value_changed_anywhere

#### Scenario: The two rows' other fields are unchanged and still classify CUDA

- **Given** the two real rows and the store's own engines registry
- **When** the guard compares each row's non-hardware fields to the base values and classifies it with the real `measurement_backend()`
- **Then** every non-hardware field is unchanged and both rows classify as CUDA, so PR #1867's guard stays green
- **Test:** tests/test_dgx_spark_hardware_clarification_1868.py::test_rows_still_classify_cuda

### Requirement: The generated README reflects only the two clarified cells

`make render-readme` SHALL regenerate `README.md` from the edited store so the two clarified hardware strings appear in the generated tables. Two consecutive renders SHALL be byte-identical and the diff SHALL be confined to those two cells and their derived cells.

#### Scenario: Render is deterministic and confined to the clarified cells

- **Given** the edited store and the regenerated README committed on the branch
- **When** `make render-readme` runs twice
- **Then** both renders are byte-identical and no unrelated README section changes
- **Test:** tests/test_dgx_spark_hardware_clarification_1868.py::test_no_other_measurement_value_changed_anywhere
