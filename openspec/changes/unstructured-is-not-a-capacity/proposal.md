# Proposal: unstructured-is-not-a-capacity

Issue: #213 (the finding, measured while attempting its backfill)

## Why

`weight_gb`'s free-text pattern was `\b\d+(?:\.\d+)?\s*(?:gb|mb)\b` — ANY capacity, in
`quant`, `hardware` or `why`. So the analysis reported **18** models as
`unstructured:weight_gb`, which reads as "the figure is there, just written as prose", when
the text actually names:

- **a card's VRAM** — `"…llama.cpp b11177 RX 9070 XT 16GB"` (`qwen3-14b`),
- **a Mac's unified memory** — `"M3 Ultra 256GB"`, `"Mac mini M4 Pro 64GB"`,
- **a context size** — `"…67K-token prompt"`.

That claim sent this work down a backfill that cannot exist: writing any of those into
`weight_gb` would put a graphics card's capacity into the weights field the card-fit table
reads. The measurement is recorded on #213; this change fixes the reporting defect behind it.

## What Changes

- **`weight_gb`'s text pattern requires a weights word** (`weights?`, `gguf`, `quants?`,
  `on disk`, `file size`) within 24 characters **of** the capacity — in either order.
- **`skip_fields`** — a new per-dimension field list — and `weight_gb` skips `hardware`
  outright: that field names the card, never the weights. The haystack builder honours it.
- **`test_a_capacity_mention_is_not_an_unstructured_weights_figure`**: a card's VRAM, a Mac's
  unified memory and a bare capacity are NOT prose weights; a stated footprint
  (`"Q4_K_M, 19GB weights"`) IS; and all of them still count as missing the **structured**
  value, because that is the real gap.

Measured on the store: `unstructured:weight_gb` falls **18 → 3**, and the 3 that remain
(`deepseek-v4.1-flash`, `qwen3.6-27b`, `muse-glimmer-30b`) genuinely mention a footprint.
Verified RED against the pre-change analysis (2 failures — every capacity counted) and GREEN
after (`PASSED 131 | FAILED 0`).

## Impact

`scripts/data_gap_analysis.py` (one pattern, one `skip_fields` entry, the haystack builder),
`tests/test_data_gap_analysis.py` (one test), this OpenSpec change and the regenerated
`OPENSPEC.md`. No target, stage, job or image changes (`ARCHITECTURE.md` unchanged).

## Not covered

- **Filling `weight_gb`** (24 of 50 models). The evidence on #213 shows the store does not hold
  a weights figure for them; that is a refresh's job, not a script's.
- **`system_ram_min`'s pattern.** It demands the word RAM next to the capacity, so
  `"M4 Max 128GB"` is not counted — correct, and its 19 missing models are the same kind of
  real gap.
