# How to gather the data for this repo

> **As of the `ci/x-trending-pipeline` work (issue #1), the README is generated**
> from `data/models.json` by `scripts/update_trending.py`. The refresh is run by
> the **GitHub Actions pipelines** invoking a **Hermes agent session**
> (deepseek-v4-flash-0731 via the Nous portal, token from the repo secret
> `NOUS_PORTAL_API_TOKEN`) that loads this skill + AGENTS.md and searches
> lightbrd.com via the Firecrawl scrape API (`FIRECRAWL_API_KEY`). Each of the
> three searches for the backend groups (NVIDIA, Metal, CPU) each write their
> own timestamped raw snapshot; they aggregate into
> `models.json`. You should **add models to the JSON store**, not hand-edit the
> tables, then run the script to regenerate. See `AGENTS.md` for the full
> operating contract (7-day trending, 30-day retention, t/s per engine,
> 8-48 GB scope, feature-branch PRs only).

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

## 2. Search queries that work — grouped by backend

Run one search group per backend, over a **last-30-day** window, and rank results
by **highest interactions first** (likes/loves + comments), then by t/s. Capture
the engine and the specific model each post tested. All queries below are
verified against the lightbrd.com mirror.

### Backend A — NVIDIA / CUDA (8–48 GB scope)
| Goal | Query |
|---|---|
| Broad RTX t/s | `rtx tokens per second llm` |
| RTX 3090 Qwen spec-decode | `rtx 3090 tokens per second qwen` |
| RTX 5090 low-end | `rtx 5090 32gb tokens per second` |
| RTX 4090 | `rtx 4090 tokens per second llm` |
| Cross-card 27B | `rtx 3090 vs 5090 27b tokens` |
| FreeToken (big MoE on small GPU) | `freetoken gpu llm tokens per second` |
| Bonsai 2 ternary | `bonsai 2 ternary 27b tokens` |
| DFlash2 spec decode | `qwen3.8-27b dflash speculative tokens` |
| General | `open weight llm benchmark gpu` |

### Backend B — Apple / Metal
| Goal | Query |
|---|---|
| Broad MLX t/s | `mlx tokens per second` |
| MLX + models | `mlx apple silicon tokens per second model` |
| M4/M-series MLX | `mac m4 mlx local llm tokens per second` |
| MLX-fast Bonsai 2 | `mlxfast bonsai tokens per second` |
| TensorFold / DFlash on MLX | `tensorfold dflash mlx qwen tokens per second` |

### Backend C — CPU (sparse on X)
| Goal | Query |
|---|---|
| No-GPU CPU runs | `llm tokens per second no gpu cpu` |
| llama.cpp CPU only | `llama.cpp cpu only tokens per second` |
| Local LLM on GPU (CPU offload) | `local llm tokens per second gpu` |

> **Probing notes (tested Sep 28 2026):** plain engine-name-only queries (e.g.
> `free%20token engine moE small gpu`) return **nothing** — FreeToken's raw
> name isn't indexed as a search term. Prefer **model + token/VRAM** queries;
> treat engine names as optional signals. CPU-only LLM benchmarking is genuinely
> sparse on X — most "CPU" signal lives in offload-capable engines (FreeToken,
> llama.cpp cpu) that appear under the CUDA/engine queries. The pipeline's CPU
> table will be thinner by nature; don't pad it with fabricated numbers. There
> is NO separate "general" search — the three backend searches (CUDA/Metal/CPU)
> already capture every model; an unfiltered general query produced a payload
> too large for the model's output cap and was removed.

## 3. Extract per model

For each model, capture:
- **Full name** (not the abbreviation)
- **Params** (total / active for MoE)
- **License**
- **HF link** (verify — see step 5)
- **VRAM / RAM** required
- **Measured t/s** + the **hardware** it was measured on
- **Inference engine** (the one that runs it best) — **with its repo URL**
  (e.g. `https://github.com/ggml-org/llama.cpp`). Store the engine `url` in
  `data/models.json` under `engines[<name>].url` so every generated table and
  the engine guide render a working link. A model row must have its HF link;
  an engine measurement must have its repo link. No bare names.

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
| **vLLM / SGLang** | CUDA | Production serving, big MoE; + DFlash2 speculative decode |
| **DFlash2** | CUDA | Spec decode + context-lookup (Inco AI / syv-ai); Qwen3.8-27B ~118-133 tok/s chat on 24 GB 3090 |
| **Strata** | CUDA | Big MoE (Qwen3.8-Flash-Next 125B) on 8-48 GB NVIDIA; experts across GPU/RAM/SSD, ~1.6-1.8x (Niko1221/Strata) |
| **MLX** | Metal | Fastest on Apple Silicon |
| **TensorFold** | Metal | Speculative decoding on Mac, 3-6x |
| **MLX-fast (Bonsai 2)** | Metal | Speedup engine for Ternary Bonsai 2 27B on Apple Silicon; ~237 tok/s on 16 GB Mac (Layr-Labs/mlxfast-bonsai2-27b-engine) |
| **TensorRT-LLM** | CUDA | Max NVIDIA perf |
| **LiteRT** | CUDA / Metal | Google's local runtime (Gemma 4 + Antigravity) |


## 3. Link repair (fix-bot) — search for a correct link, never invent one

When CI validation (`scripts/validate.py check_links_resolve`) reports a dead or
wrong link, the fix-bot (Hermes) must SEARCH for the correct link and verify it
resolves before writing it. CI itself never calls the LLM — it only reports.

- **Model / format Hugging Face link** (`model-hf`, `format-hf`, `raw-hf`): find
  the canonical repo id with the Hugging Face CLI / `huggingface_hub` — e.g.
  `hf search models <name>` or the HF API `https://huggingface.co/api/models?search=<name>`.
  Confirm `https://huggingface.co/<id>` returns 200 before writing it.
- **Engine / inference-server link** (`engine-registry`, `source_post`): do a
  regular Firecrawl web search (`FIRECRAWL_API_KEY`) for the engine's canonical
  repo URL and confirm it resolves. Known-good engine repos live in
  `KNOWN_ENGINE_URLS` in `scripts/validate.py`.
- Only write a link you have actually verified resolves. If you cannot find a
  verified replacement, leave the link and report it in the PR body for manual
  review. Never invent a URL.
- Update `data/models.json` (and the raw snapshot if the wrong link came from
  `data/raw/*.json`), then regenerate `README.md` via `scripts/update_trending.py`.


## 4. Engagement-weighted t/s (aggregation) — the search agent MUST record per-post engagement

The aggregator (`scripts/update_trending.py` `merge_engines`) weights each engine
measurement's t/s by the **engagement on its source X post**. For this to work,
the search agent MUST record, on **every engine measurement**, the source post's
numeric engagement:

- `likes`, `comments`, `reshares`, `views`, `interactions` (all integers >= 0).

The composite weight is `likes + 2*comments + 3*reshares + log10(views+1)` —
reshares are the strongest signal (active endorsement + reach), comments next,
likes passive, views log-scaled so a viral-but-unverified post can't dominate.

How it behaves (all covered by unit tests):
- **Concordant t/s** (within 12%) collapse to one row whose representative is the
  engagement-weighted mean of the concordant cores.
- **keep-higher**: the representative is `max(highest reported t/s, weighted mean)`
  — a reported t/s is only ever RAISED, never lowered by a noisy low-engagement
  outlier.
- **Higher t/s than the one already in models.json is UPDATED** (not duplicated);
  a brand-new model is CREATED with the engagement-weighted t/s.
- Genuinely different t/s (beyond tolerance), different GPU, or different engine
  stays a distinct row.

If a measurement lacks engagement, it is defaulted to 0 (weight 1) — but the
agent should always try to capture the real numbers, because without them the
weighting is inert.
