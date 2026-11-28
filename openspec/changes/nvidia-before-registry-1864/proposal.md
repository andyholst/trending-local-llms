Issue: #1864

# Proposal: nvidia-before-registry-1864

Closes #1864.

## Why

`measurement_backend()` checked the engine registry before NVIDIA hardware tokens. TensorFold and MLX are registered to a single non-CUDA backend because their common use is on Apple Silicon, but 13 live measurements name NVIDIA hardware in their `hardware` field (RTX 5060 Ti, RTX 4090, RTX 5090, NVIDIA DGX Spark / GB10). They rendered in the Metal columns: the "Most loved" Metal best cell for Qwen3.8-27B showed a 1045 t/s COLD PREFILL figure measured on an NVIDIA DGX Spark. AMD hardware already wins over the registry; NVIDIA hardware did not.

## What Changes

- Add `is_nvidia_gpu()` beside `is_amd_gpu()` in `scripts/update_trending.py` and consult it BEFORE the engine registry lookup in `measurement_backend()`, using the existing `_CUDA_HW` token set (rtx / nvidia / cuda / geforce / tesla / a100 / h100 / l40 / aic).
- Keep explicit Apple/Mac hardware and explicit CPU-only wording at higher priority, so a real TensorFold-on-Mac row still renders Metal and a CPU-only row still renders CPU.
- Add a real-file guard (`tests/test_nvidia_before_registry.py`) that drives the REAL classifier over the REAL shipped store and its engines registry: the 13 rows named in #1864 classify CUDA, every explicit-NVIDIA row wins over its registry backend, and TensorFold-on-Mac remains Metal. No stand-ins or monkeypatch (rule 6m).
- Regenerate `README.md` from the unchanged store: the 1045 t/s DGX Spark figure moves out of the Metal best cell into CUDA.

## Impact

Classifier-order fix only. No data value, schema, contract, API, table shape, Makefile target, pipeline job or image changes. `data/models.json` and the snapshot history are untouched; only the generated README changes as a consequence of the corrected classification. Apple/Mac and CPU-only precedence is preserved. No cron and no Actions schedule added.

## Not covered

- Adding new hardware tokens to `_CUDA_HW` (DGX Spark rows that name no NVIDIA/CUDA token keep their existing classification).
- Changing the engines registry entry for TensorFold or MLX (they remain registered as Metal — the fix is hardware precedence, not registry data).
- An `AGENTS.md` §8 rulebook row for the new guard: if rule 6c review requires one, it is declared on the issue as `- [~] … — blocked: rule 3c human sign-off` and landed by an attended change, never written headlessly.
