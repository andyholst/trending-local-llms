# How to gather the data for this repo

This repo tracks open-weight LLMs people actually run and like, based on **community-reported data from X posts**. Here's the exact workflow used to build and update the README.

## 1. Reach X content (the key trick)

**Firecrawl / web_extract does NOT support x.com** — it returns `Website Not Supported`. Don't waste calls on it.

Use the **lightbrd.com mirror** (a working X frontend) via `web_extract`:

```
https://lightbrd.com/search?f=tweets&q=QUERY
```

- URL-encode the query. `f=tweets` filters to posts.
- lightbrd returns real X posts with author, timestamp, text, and engagement (likes/views).
- Nitter instances (nitter.net, xcancel.com, nitter.poast.org, nitter.privacydev.net) are mostly down or blocked — don't rely on them.
- lightbrd results are truncated; the full text is saved to a cache file (the footer gives the path). Read it with `read_file` to get the omitted middle.

## 2. Search queries that work

| Goal | Query |
|---|---|
| General speed | `"tokens per second" local llm` |
| Open-weight benchmarks | `open weight llm benchmark gpu` |
| Specific model | `qwen3.8-27b local speed tokens` |
| Specific model | `gemma 4 12b tokens per second` |
| Apple Silicon | `mlx apple silicon tokens per second benchmark` |
| High VRAM | `48GB 64GB 96GB VRAM llm benchmark` |
| Unified memory | `128GB 256GB unified memory llm benchmark` |
| Model families | `llama 4 open weights release`, `deepseek open weights local`, `glm kimi nemotron open weight local` |

## 3. Extract per model

For each model, capture:
- **Full name** (not the abbreviation)
- **Params** (total / active for MoE)
- **License**
- **HF link** (verify — see step 5)
- **VRAM / RAM** required
- **Measured t/s** + the **hardware** it was measured on
- **Inference engine** (the one that runs it best)

## 4. Rank by engagement, not benchmarks

Rank models by what people actually love on X:
- View counts, like counts, comment counts from the posts
- HF download counts
- Repeated mentions across many posts

This is **directional**, not a precise like-count. Note it as such.

## 5. Verify HF links

Model IDs often differ from the marketing name. Verify with a web search:

```
Qwen3-235B-A22B huggingface
```

Known gotchas:
- **Qwen3.8-Max** → `Qwen/Qwen3.8-2.4T-A95B`
- **Mach-1 Additive** → `SyzygyResearch/Mach-1-Additive-35B`

## 6. README structure

- **"Most loved" table** ranked by engagement, with: rank, model, full name, HF link, why people love it, **CUDA t/s**, **Metal t/s**, VRAM, engine.
- **GPU type first**: CUDA (NVIDIA), then CPU, then Metal (Apple Silicon).
- **VRAM tiers** within each: 6/8/12/16/24/32/48/64/96/128/256/384/512/576 GB (CUDA), 48/64/96/128/256/512 (Metal), by RAM (CPU).
- **Same column pattern per tier**: Model | Params | License | HF | VRAM | t/s | Engine.
- **Sort by highest t/s** within each tier.
- **One specific engine per model** — not a list.
- Include a **speed-evolution** section (same model, faster engines over months) and an **engine guide**.

## 7. Honesty rules

- Community-reported X data is **directional, not lab-grade**. Mark estimates as `(est)`.
- Don't present vendor claims as independent benchmarks.
- Don't scrape/replicate one person's curation as your own — compile from broad public X signal and attribute each model to its actual creator.
- VRAM figures are estimates from quant sizes unless a post gives a measured number (e.g. Qwen3.8-27B has a precise VRAM-sizing formula).
- High-VRAM tiers (48 GB+) lean on a few detailed X writeups — fewer measured numbers there.

## Engines to know

| Engine | Backend | Best for |
|---|---|---|
| **Ollama** | CUDA / CPU / Metal | Easiest start |
| **llama.cpp** | CUDA / CPU / Metal | Max control, custom quants (Bonsai 2, Mirai 2.4-bit) |
| **FreeToken** | CUDA | 2-4x faster than Ollama; big MoE on small GPUs |
| **vLLM / SGLang** | CUDA | Production serving, big MoE |
| **MLX** | Metal | Fastest on Apple Silicon |
| **TensorFold** | Metal | Speculative decoding on Mac, 3-6x |
| **TensorRT-LLM** | CUDA | Max NVIDIA perf |
| **LiteRT** | CUDA / Metal | Google's local runtime (Gemma 4 + Antigravity) |
