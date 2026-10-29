# How to gather the data for this repo

> **As of the `ci/x-trending-pipeline` work (issue #1), the README is generated**
> from `data/models.json` by `scripts/update_trending.py`. The refresh is run by
> the **GitHub Actions pipelines** invoking a **Hermes agent session**
> (deepseek-v4-flash-0731 via the Nous portal, token from the repo secret
> `NOUS_PORTAL_API_TOKEN`) that loads this skill + AGENTS.md and searches
> lightbrd.com via the Firecrawl scrape API (`FIRECRAWL_API_KEY`). Each of the
> four searches for the backend groups (NVIDIA, Metal, CPU, AMD) each write their
> own timestamped raw snapshot; they aggregate into
> `models.json`. You should **add models to the JSON store**, not hand-edit the
> tables, then run the script to regenerate. See `AGENTS.md` for the full
> operating contract (7-day trending, 30-day retention, t/s per engine,
> 8-48 GB scope, feature-branch PRs only).

This repo tracks open-weight LLMs people actually run and like, based on **community-reported data from X posts**. Here's the exact workflow used to build and update the README.

## 1. Reach X content (the key trick)

**Firecrawl / web_extract does NOT support x.com** — it returns `Website Not Supported`. Don't waste calls on it.

### The Firecrawl header — the value comes from the environment, and is never printed

The scrape call authenticates with `Authorization: Bearer ${FIRECRAWL_API_KEY}`: **read the VALUE
from the environment and never print, echo, log or write it anywhere** — not in a summary, not in a
snapshot, not in a message to a human. The pipeline sets it (the `FIRECRAWL_API_KEY` environment
variable, forwarded by NAME from the repo secret; `make search-<backend>` fails loudly before you
start when it is missing or empty, issue #357).

If a call returns `401`, that is a **BLOCKER**: report it and stop. Do **not** go looking for a key —
do not search the filesystem, do not quote `~/.hermes/.env`, do not ask a human to supply one, and
never write an `export FIRECRAWL_API_KEY=…` line (with a value or a placeholder) into output: the
log is public, and a placeholder is one paste away from the real thing (issue #355). A leg that
cannot authenticate must fail, never narrate its search.

**Make the call from the TERMINAL tool — never from `execute_code`** (issue #362). The terminal's
child process is the only one Hermes leaves the key in: `execute_code`'s child environment is scrubbed
of every credential-shaped name and does not unwrap `_HERMES_FORCE_`, so a scrape made there sends an
**empty** Bearer and fails `HTTP 401` while the key is set. `python3 scripts/update_trending.py
--fetch`, run from the terminal, reads the key in-process and is fine.

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

### Backend D — AMD / ROCm (Radeon 8–48 GB + Strix Halo APUs)
| Goal | Query |
|---|---|
| RX 7900 XTX t/s | `rx 7900 xtx tokens per second` |
| RX 9070 XT t/s | `rx 9070 xt tokens per second` |
| ROCm runs | `rocm tokens per second` |
| llama.cpp Vulkan on AMD | `llama.cpp vulkan amd tokens` |
| Strix Halo / Ryzen AI Max | `strix halo tokens per second` |
| (`--fetch` path only) 7900 XTX + model | `rx 7900 xtx qwen` |

> **AMD probing notes (tested Oct 2 2026):** AMD posts name the **card** far
> more than the API — query by card (`rx 7900 xtx`, `rx 9070 xt`, `strix halo`)
> rather than `rocm` alone. Record the card in `hardware` exactly as posted
> (`RX 7900 XTX 24GB`, `Radeon 8060S / Strix Halo 128GB`): the hardware is what
> classifies a figure as ROCm, whatever engine ran it. Keep the engine's
> registry name (`llama.cpp`, `vLLM`, `Strata` …) and put the API (`ROCm`,
> `HIP`, `Vulkan`) in `quant` — never `llama.cpp (Vulkan)` as an engine.
> Vulkan also runs on NVIDIA/Intel, so Vulkan alone is not AMD. Strix Halo
> posts often quote **prompt-processing / prefill** t/s (1,000+): skip those,
> record generation t/s only. Datacenter Instinct (MI300/MI355) is out of scope.
> lightbrd (a Nitter front end) prints a post's counts without labels, zeros
> omitted, in Nitter's order replies · reposts · quotes · likes · views — so 4
> numbers on a post with no quotes are replies, reposts, likes, views (the
> coldniko RX 7900 XTX post: 41 · 59 · 504 · 38,670).

> **Probing notes (tested Sep 28 2026):** plain engine-name-only queries (e.g.
> `free%20token engine moE small gpu`) return **nothing** — FreeToken's raw
> name isn't indexed as a search term. Prefer **model + token/VRAM** queries;
> treat engine names as optional signals. CPU-only LLM benchmarking is genuinely
> sparse on X — most "CPU" signal lives in offload-capable engines (FreeToken,
> llama.cpp cpu) that appear under the CUDA/engine queries. The pipeline's CPU
> table will be thinner by nature; don't pad it with fabricated numbers. There
> is NO separate "general" search — the four backend searches (CUDA/Metal/CPU/ROCm)
> already capture every model; an unfiltered general query produced a payload
> too large for the model's output cap and was removed.

> **Query the low end on purpose (issue #337).** The index is for a GAMING LAPTOP
> first — 8 to 24 GB of VRAM. Measured against the store: 30 of 46 models had no
> CUDA/ROCm figure on a card ≤ 24 GB and 37 none ≤ 16 GB, because every card query
> named a 3090/4090/5090 (24-32 GB) or an RX 7900 XTX/9070 XT. So the CUDA and AMD
> legs now carry the owner cards too (`rtx 3060`, `rtx 4060`, `rtx 4060 ti 16gb`,
> `rtx 4070`, `8gb vram`, `16gb vram`, `rx 7600`, `rx 6600`, `rx 9060 xt`,
> `radeon 8gb vram`). A tier with no figure is reported as a collection gap in the
> README — which is the honest answer, and the reason to run these queries.

> **Trending-model queries (issue #264).** The lists above are fixed and name no
> model: of the 24 queries the ONE model-specific one names `qwen3.8-27b`, and
> none names `Strata`, so every figure for the model at the top of the README
> arrived incidentally and a higher one upstream could never be found. So each
> search leg ALSO runs the **trending-model queries** — TWO per model in the top
> `QUERY_TOP_N` (10) of `data/models.json`: one for its throughput, naming the
> model by its own id (`<id> tokens per second`), and one for its footprint
> (`<id> vram ram context weights`). The second exists because a post that
> answers a throughput query can legitimately state no VRAM, weight size, context
> window or engine build — which is exactly why those dimension gaps stayed open
> while every ranked model already had captured rows. They are derived from the
> store by `scripts/update_trending.py` (ONE implementation, rule 6d) and reach
> the prompts as `$(MODEL_QUERIES)`; `python3 scripts/query_coverage.py --queries`
> prints exactly what a prompt sends, and `make query-coverage` reports the
> curated-only reach against the full set — 10 of the top 10 once the derived
> queries are added — and **FAILS** when a model is named by no query, so when
> you add a model, the pipeline says so instead of silently capping what we know.

## 3. Extract per model

For each model, capture:
- **Full name** (not the abbreviation)
- **Params** (total / active for MoE)
- **License**
- **HF link** (verify — see step 5)
- **VRAM / RAM** required
- **System RAM / unified memory** the post states (e.g. a Raspberry Pi / laptop
  figure) — record it as the OPTIONAL model field `system_ram_min`, never
  derived from the VRAM number: the CPU and Metal tables are RAM-bound (Apple
  Silicon is unified memory) and partial offload keeps the un-offloaded layers
  plus the KV cache in system RAM.
- Also optional, and ONLY when the post states the figure — never guessed:
  `weight_gb` (weight footprint per format + quant, e.g. `5.95GB Q4_K_M`),
  `context_tokens` (context window, e.g. `131072` / `128K`),
  `storage_offload` (experts streamed from storage, e.g. `640GB NVMe`),
  `engine_min_version` (the engine build or flags the figure needs, e.g.
  `llama.cpp b6xxx --n-gpu-layers 99`). Leave a field out entirely rather than
  inventing a value — an absent field is reported as a gap, a wrong one is a
  fabrication.
- **And put the footprint on the MEASUREMENT, not only on the model**, when the
  post gives it for THAT run: `weight_gb` / `context_tokens` / `system_ram_min` /
  `storage_offload` are allowed on a measurement too (issue #337). One model's
  quants fit different cards, and the README's card-fit tables are built from
  this: a t/s figure whose own card is known but whose weights are 6 GB is what
  tells an 8 GB owner the model can run for them. A measurement with no footprint
  can only prove the card it ran on.
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

The leg's shell carries `HF_TOKEN`, so a `https://huggingface.co/api/models?search=<name>`
lookup is authenticated: an unauthenticated one is rate-limited and answers `401`/`429`
for a gated repo, which reads as "no such model" and gets you the marketing name
(issue #363). Send it by NAME — `-H "Authorization: Bearer $HF_TOKEN"` — and never
print, echo or write the value anywhere (AGENTS.md §3d).

Known gotchas:
- **Qwen3.8-Max** → `Qwen/Qwen3.8-2.4T-A95B`
- **Mach-1 Additive** → `SyzygyResearch/Mach-1-Additive-35B`

## 6. README structure

- **"Most loved" table** ranked by engagement, with: rank, model, full name, HF link, why people love it, **CUDA t/s**, **Metal t/s**, **CPU t/s**, **ROCm t/s**, VRAM, engine.
- **GPU type first**: CUDA (NVIDIA), ROCm (AMD), then CPU, then Metal (Apple Silicon).
- **VRAM tiers** within each: 6/8/12/16/24/32/48/64/96/128/256/384/512/576 GB (CUDA), 8/12/16/20/24/32/48 GB (ROCm), 48/64/96/128/256/512 (Metal), by RAM (CPU).
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
| **Ollama** | CUDA / ROCm / CPU / Metal | Easiest start |
| **llama.cpp** | CUDA / ROCm / CPU / Metal | Max control, custom quants (Bonsai 2, Mirai 2.4-bit); AMD via ROCm/HIP or Vulkan |
| **FreeToken** | CUDA | 2-4x faster than Ollama; big MoE on small GPUs |
| **vLLM / SGLang** | CUDA / ROCm | Production serving, big MoE; + DFlash2 speculative decode |
| **DFlash2** | CUDA | Spec decode + context-lookup (Inco AI / syv-ai); Qwen3.8-27B ~118-133 tok/s chat on 24 GB 3090 |
| **Strata** | CUDA / ROCm | Big MoE (Qwen3.8-Flash-Next 125B) on 8-48 GB NVIDIA or AMD (`--backend hip`); experts across GPU/RAM/SSD, ~1.6-1.8x (Niko1221/Strata) |
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
