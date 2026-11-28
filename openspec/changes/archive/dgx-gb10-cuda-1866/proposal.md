Issue: #1866
PR: #1867

# Proposal: dgx-gb10-cuda-1866

Closes #1866.

## Why

PR #1865 made explicit NVIDIA hardware outrank the engine registry, but its `_CUDA_HW` vocabulary omitted the two tokens that name the DGX Spark box itself: `dgx` and `gb10`. Three TensorFold rows name a DGX Spark with no vendor token and still classify Metal (qwen3.8-flash-next-125b "DGX Spark" 67 t/s and "DGX Spark (GB10, 128GB), TP1" 39.3 t/s; glm-5.3-flash "2x DGX Spark (200 Gb/s link)" 109.1 t/s). Adding the tokens also shifts three more rows from ROCm; all six are enumerated and decided in `findings/1866.md`.

## What Changes

- Append `dgx` and `gb10` to the ONE `_CUDA_HW` token set in `scripts/update_trending.py`, so the NVIDIA-before-registry guard, `is_amd_gpu()`'s "no NVIDIA token" exclusion, the CPU-vs-GPU check and the keyword fallback all read the same vocabulary. No second token list, no per-row exception.
- Add a real-file guard (`tests/test_dgx_gb10_cuda.py`) that drives the REAL classifier over the REAL shipped store (models + measurements + posts via `flatten_store`) and its own engines registry, with no stand-ins or monkeypatch (rule 6m). It asserts the three #1866 rows classify CUDA, all 36 DGX/GB10 rows are CUDA, every one of the six enumerated delta rows matches its documented decision, and Apple/Mac and explicit-CPU-only precedence is unchanged.
- Record the full before/after delta and its evidence-backed per-row decisions in `findings/1866.md`. No data value is edited.
- Regenerate `README.md` from the unchanged store: the DGX Spark figures leave the Metal column; two renders are byte-identical.

## Impact

Classifier-vocabulary fix only. No data value, schema, contract, API, table shape, Makefile target, pipeline job or image changes. `data/models.json` and the snapshot history are untouched; only the generated README changes as a consequence of the corrected classification. Apple/Mac and CPU-only precedence is preserved. No cron and no Actions schedule added.

## Not covered

- Editing the data to resolve the contradictory `Radeon 8060S / Strix Halo 128GB (ASUS Ascent GX10, GB10)` hardware strings; that is recorded as a separate finding in `findings/1866.md` for a future, separately dispatched data change.
- Changing the engines registry entry for TensorFold, MLX or ExLlamaV3 (ROCm fork) — they keep their registry backends; the fix is hardware precedence.
- An `AGENTS.md` §8 rulebook row for the new guard: if rule 6c review requires one, it is declared on issue #1866 as `- [~] … — blocked: rule 3c human sign-off` and landed by an attended change, never written headlessly.
