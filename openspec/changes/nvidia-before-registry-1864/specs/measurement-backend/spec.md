## ADDED Requirements

### Requirement: Explicit NVIDIA hardware outranks a single-backend registry entry

`scripts/update_trending.py::measurement_backend()` SHALL check the measurement's `hardware` for an explicit NVIDIA/CUDA token from `_CUDA_HW` and return `CUDA` BEFORE consulting the engines registry or the built-in engine-to-backend map. The check SHALL be the NVIDIA analogue of the existing AMD-before-registry guard and SHALL live in one helper (`is_nvidia_gpu()`) beside `is_amd_gpu()`. Explicit Apple/Mac hardware and explicit CPU-only wording SHALL keep higher priority.

#### Scenario: All 13 reported NVIDIA/TensorFold rows classify CUDA

- **Given** the real shipped store flattened by `load_store()` with its real engines registry, including the 13 rows named in issue #1864 (RTX 5060 Ti, RTX 4090, RTX 5090, NVIDIA DGX Spark / GB10)
- **When** `measurement_backend()` classifies each measurement
- **Then** every one returns `CUDA`, including the 1045 t/s DGX Spark cold-prefill figure, and none returns `Metal`
- **Test:** tests/test_nvidia_before_registry.py::test_named_rows_are_cuda

#### Scenario: Every explicit-NVIDIA row wins over its registry backend

- **Given** the real shipped store and its real engines registry
- **When** every measurement whose hardware carries an `_CUDA_HW` token is classified
- **Then** none is classified as a non-CUDA backend by a registered single-backend engine
- **Test:** tests/test_nvidia_before_registry.py::test_every_explicit_nvidia_row_wins_over_registry

#### Scenario: A TensorFold-on-Mac row still classifies Metal

- **Given** a TensorFold measurement whose hardware names Apple/Mac, or hardware with explicit CPU-only wording
- **When** `measurement_backend()` classifies it
- **Then** Apple/Mac hardware returns `Metal` and explicit CPU-only wording returns `CPU`, even though the engine is registered to Metal and a CUDA token may also be present
- **Test:** tests/test_nvidia_before_registry.py::test_apple_and_cpu_only_keep_priority

### Requirement: The generated README reflects the corrected classification

`make render-readme` SHALL regenerate the README from the unchanged store so the 1045 t/s NVIDIA DGX Spark figure is no longer the Metal best cell; two consecutive renders SHALL be byte-identical.

#### Scenario: Render moves the DGX Spark figure out of the Metal best cell

- **Given** the corrected classifier and the unchanged store
- **When** `make render-readme` runs twice
- **Then** both renders are byte-identical, the Qwen3.8-27B "Most loved" CUDA best cell contains the 1045 t/s DGX Spark figure, the Metal best cell does not, and no unrelated section changes
- **Test:** tests/test_nvidia_before_registry.py::test_named_rows_are_cuda
