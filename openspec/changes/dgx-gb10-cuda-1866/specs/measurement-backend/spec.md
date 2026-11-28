## ADDED Requirements

### Requirement: DGX Spark and GB10 are NVIDIA hardware tokens in the one CUDA vocabulary

`scripts/update_trending.py::_CUDA_HW` SHALL contain `dgx` and `gb10` in addition to its existing tokens. Because `_CUDA_HW` is the single vocabulary read by `is_nvidia_gpu()`, by `is_amd_gpu()`'s "and no NVIDIA token" exclusion, by the CPU-vs-GPU check and by the keyword fallback, a measurement whose hardware names a DGX Spark or GB10 SHALL classify as `CUDA` BEFORE the engines registry or the built-in engine-to-backend map is consulted, including when the engine is registered to another single backend (TensorFold/MLX -> Metal, ExLlamaV3 (ROCm fork) -> ROCm). Explicit Apple/Mac hardware and explicit CPU-only wording SHALL keep higher priority.

#### Scenario: The three rows named in #1866 classify CUDA

- **Given** the real shipped store flattened by `flatten_store()` with its real engines registry, including `qwen3.8-flash-next-125b` / TensorFold / "DGX Spark" / 67 t/s, `qwen3.8-flash-next-125b` / TensorFold / "DGX Spark (GB10, 128GB), TP1 (decode tests on two Sparks)" / 39.3 t/s and `glm-5.3-flash` / TensorFold / "2x DGX Spark (200 Gb/s link)" / 109.1 t/s
- **When** `measurement_backend()` classifies each measurement
- **Then** every one returns `CUDA` and none returns `Metal`
- **Test:** tests/test_dgx_gb10_cuda.py::test_named_rows_are_cuda

#### Scenario: Every DGX/GB10 row in the real store classifies CUDA

- **Given** the real shipped store and its real engines registry, with no stand-ins and no monkeypatch
- **When** every measurement whose hardware or quant names DGX or GB10 is classified
- **Then** none is classified as a non-CUDA backend
- **Test:** tests/test_dgx_gb10_cuda.py::test_every_dgx_gb10_row_is_cuda

#### Scenario: Every enumerated before/after delta row matches its documented decision

- **Given** the six `- DELTA ` rows recorded in `findings/1866.md` (three TensorFold rows Metal -> CUDA, two qwen3.6-35b-a3b rows ROCm -> CUDA, one minicpm-v-4.7 row ROCm -> CUDA), each decided `shift-correct` on explicit NVIDIA hardware evidence
- **When** the real-file guard finds each row in the real store and classifies it
- **Then** its actual classification equals its recorded decision and its recorded before/after values differ
- **Test:** tests/test_dgx_gb10_cuda.py::test_enumerated_delta_matches_its_decision

#### Scenario: Apple/Mac and explicit CPU-only precedence is unchanged

- **Given** a TensorFold measurement on Apple/Mac hardware, a real TensorFold-on-Mac row, and a DGX-Spark row with explicit CPU-only wording
- **When** `measurement_backend()` classifies them
- **Then** Apple/Mac hardware still returns `Metal` and explicit CPU-only wording still returns `CPU`
- **Test:** tests/test_dgx_gb10_cuda.py::test_apple_and_cpu_only_keep_priority

### Requirement: The generated README reflects the DGX reclassification

`make render-readme` SHALL regenerate the README from the unchanged store so the DGX Spark figures are no longer in the Metal column; two consecutive renders SHALL be byte-identical and no unrelated section SHALL change.

#### Scenario: Render moves the DGX Spark figures out of Metal

- **Given** the corrected classifier and the unchanged store
- **When** `make render-readme` runs twice
- **Then** both renders are byte-identical, the GLM-5.3-Flash 109.1 t/s TensorFold DGX figure renders in the CUDA column rather than Metal, and the diff is confined to the six reclassified rows and their derived best cells
- **Test:** tests/test_dgx_gb10_cuda.py::test_named_rows_are_cuda
