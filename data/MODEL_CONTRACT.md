# data/models.json — Model Contract

`data/models.json` is the **single source of truth** for the trending-local-llms
index. The README is generated from it. Every model is one object in the
`models` array. **No duplicate models** (by `id` or `name`) are allowed — the
validator enforces this.

> **Machine-checkable schema:** the exact contract is defined in
> `data/model_contract.json` (JSON Schema 2020-12). `scripts/validate.py`
> (check_schema) validates `models.json` against it on every run. The prose
> below summarises it; the schema is authoritative.

## Top-level shape

```json
{
  "generated_utc": "2026-09-28T12:00:00Z",
  "note": "...",
  "engines": { "<engine-name>": { "backend": "...", "note": "...", "url": "https://github.com/..." } },
  "models": [ { ...model... }, { ...model... } ]
}
```

- `engines` — the engine registry. Every engine a model references must exist
  here with a `url` (repo link). The README engine guide is built from this.
  `backend` is one of CUDA, ROCm, Metal, CPU or several joined with ` / ` in
  the canonical order CUDA, ROCm, CPU, Metal (e.g. `CUDA / ROCm / CPU / Metal`).
- `models` — the list of models. **No duplicates.**

## Model object contract

Each entry in `models` has exactly this shape:

```json
{
  "id": "bonsai-2-27b",
  "name": "Bonsai 2 27B",
  "full_name": "Ternary-Bonsai-2-27B",
  "type": "LLM (ternary)",
  "formats": [
    { "name": "GGUF", "hf": "prism-ml/Ternary-Bonsai-2-27B-gguf" },
    { "name": "MLX", "hf": "prism-ml/Ternary-Bonsai-2-27B-gguf" }
  ],
  "license": "Apache 2.0",
  "params": "27B",
  "hf": "prism-ml/Ternary-Bonsai-2-27B-gguf",
  "vram_tier": "12GB",
  "vram_min": "8GB",
  "backends": ["CUDA", "Metal", "CPU", "ROCm"],
  "supported_engines": ["llama.cpp", "MLX-fast (Bonsai 2)"],
  "engines": [
    {
      "engine": "llama.cpp",
      "tps": "67-71",
      "hardware": "RTX 5060 Ti 16GB",
      "quant": "MTP head",
      "date": "2026-09-27",
      "source_post": "https://lightbrd.com/sudoingX"
    }
  ],
  "why": "One-line reason people love it.",
  "engagement": { "likes": 2750, "comments": 640, "views": 84563, "last_7d_likes": 1420 },
  "last_seen": "2026-09-27"
}
```

### Field meanings

| Field | Required | Meaning |
|---|---|---|
| `id` | yes | Unique slug. **No duplicates.** |
| `name` | yes | Short display name. **No duplicates.** |
| `full_name` | yes | Full model name. |
| `type` | yes | Model type (LLM, LLM (ternary), MoE, etc.). |
| `formats` | yes | Weight formats, **each `{ name, hf }` with its own Hugging Face link**. One entry per format. |
| `license` | yes | License. |
| `params` | yes | Parameter count (total / active for MoE). |
| `hf` | yes | Primary Hugging Face repo id → `https://huggingface.co/<hf>`. |
| `vram_tier` | yes | VRAM category (8GB, 12GB, 16GB, 24GB, 32GB, 48GB). |
| `vram_min` | yes | **LEAST required VRAM** needed to run the model (e.g. 8GB). Community-reported from the X measurement posts; cross-checked against the smallest usable quant file size on Hugging Face (HF does not expose a VRAM field — see note below). |
| `backends` | yes | Backends it runs on (CUDA, Metal, CPU, ROCm = AMD GPUs). Must include every backend its measurements render in — ingest adds it (`sync_backends`); AMD hardware (Radeon / RX / Strix Halo / ROCm) is ROCm whatever the engine. |
| `supported_engines` | yes | **List of engines the model is supported by.** Each must have a measurement in `engines`. |
| `engines` | yes | **Per-engine t/s measurements** — the core data. One entry per (engine, date). |
| `why` | yes | Why people love it. |
| `engagement` | yes | X engagement: likes, comments, views, last_7d_likes. |
| `last_seen` | yes | Last date the model was seen trending (YYYY-MM-DD). |

### About VRAM / Hugging Face metadata

**Hugging Face does NOT expose a "VRAM required" field.** The model `cardData`
contains only license / name / tags. The HF API *does* return file sizes
(`?blobs=true`) — the **smallest usable quant file size** in the repo is a good
proxy for minimum VRAM (e.g. Bonsai 2's 5.95 GB PTQ1_0 ≈ 8 GB min). We do not
invent a VRAM number: `vram_min` is **community-reported from the X measurement
posts** and cross-checked against HF quant-file sizes. `vram_tier` is the coarse
category for the README tables.

### The `engines` array — t/s per engine

This is the heart of the contract. Each measurement:

```json
{
  "engine": "llama.cpp",
  "tps": "67-71",
  "hardware": "RTX 5060 Ti 16GB",
  "quant": "MTP head",
  "date": "2026-09-27",
  "source_post": "https://lightbrd.com/sudoingX"
}
```

- `engine` — must exist in the top-level `engines` registry (which has its repo `url`).
- `tps` — tokens/sec, always **per engine**. A bare number with no engine is invalid.
- `hardware` — the hardware it was measured on.
- `quant` — quantization.
- `date` — measurement date (YYYY-MM-DD).
- `source_post` — the X post (lightbrd.com) the figure came from.

## Rules enforced by `scripts/validate.py`

1. **No duplicate models** (by `id` or `name`).
2. **No model removed** vs the previous snapshot.
3. Every model has all required fields + at least one engine measurement with
   engine name + t/s + repo link.
4. `supported_engines` lists engines that each have a measurement.
5. Backend tables sorted by highest t/s descending.
6. **JSON <-> README sync**: every model + engine measurement in the JSON appears
   in the README, and the "Last generated" timestamp matches — both change
   together.
7. Every model in the store appears in the README.
