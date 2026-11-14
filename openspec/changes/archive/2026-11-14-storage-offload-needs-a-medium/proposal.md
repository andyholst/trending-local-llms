# Proposal: storage-offload-needs-a-medium

Issues: #413 (full finding) · #367 (its truncated duplicate)

## Why

The `storage_offload` dimension's free-text detector was
`re.compile(r"\bssd\b|\bdisk\b|\boffload", re.I)` — three words, anywhere. Measured on the
store, every model it reported as naming a storage offload in prose named something else:

- `qwen3.8-35b-a3b` — `"Q4_K_M with 26 MoE layers offloaded to the CPU"` (**RAM** offload)
- `qwen3.6-35b-a3b` — `"experts in system RAM"`
- `qwen3-4b` — `"4-bit MLX, 2.1GB on disk"` (a **file size**)
- `lfm2.5-24b-a2b` — `"expert layers offloaded to CPU"`
- `laya-mlx-decision-models` — `"offloads routing … calls from a big LLM"` (an **API** offload)

A genuine requirement — `"experts streamed from NVMe SSD"` — was indistinguishable from those,
so `unstructured:storage_offload` ranked as a real gap on false positives and the same models
were re-filed on every refresh.

## What Changes

- **The detector requires a storage MEDIUM and an offload/streaming word in the same
  sentence**, in either order: `offload*/stream*/expert*/mmap*` within 32 characters of
  `ssd|nvme|flash|disk|hdd|storage`.
- **`test_a_storage_offload_needs_a_medium_and_an_offload`** asserts **both directions**: a
  RAM offload, `"experts in system RAM"`, `"2.1GB on disk"` and a machine's own `"2TB SSD"`
  are not flagged; `"experts streamed from NVMe SSD"` and `"MoE expert offload to SSD"` are.

Measured on the store: the false-positive set falls to **zero**, and the guard proves a
genuine mention still counts. Verified RED against the pre-change detector (3 failures — the
RAM story, the file size and the machine's SSD were all flagged) and GREEN after
(`PASSED 133 | FAILED 0`).

## Impact

`scripts/data_gap_analysis.py` (one pattern), `tests/test_data_gap_analysis.py` (one test),
this OpenSpec change and the regenerated `OPENSPEC.md`. No target, stage, job or image
changes (`ARCHITECTURE.md` unchanged).

## Not covered

- **`system_ram_min`, `context_tokens` and `engine_min_version`'s detectors** (#214 and
  friends) — each is its own evidence-carrying change.
- **Filling the dimension.** `storage_offload` is still missing on most models; this makes the
  report say so honestly instead of naming five models that never claimed it.
