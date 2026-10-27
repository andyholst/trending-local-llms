---
name: data-search
description: Use when a trending-local-llms refresh leg must scrape X posts for one backend from the lightbrd.com mirror and write per-query raw snapshots — never a bulk payload, never a fabricated figure, never an engine invented from a model or a quant.
version: 2.0.0
author: Asimov Agent
license: CC-BY-4.0
metadata:
  hermes:
    tags: [trending-local-llms, refresh, search, firecrawl, lightbrd]
---

# One backend's refresh search

This is the leg that turns X posts into `data/raw/<backend>-<UTC>.json`. Four legs run in
parallel (`nvidia`, `metal`, `cpu`, `amd`); each is given its own keyword list and writes only its
own snapshots. **The rules live here, in full.** A leg's recipe is a pointer plus that run's
parameters — never a second copy of this file.

## Inputs

The prompt carries this run's parameters. Nothing else is a rule to re-derive:

- **`backend`** — one of `nvidia`, `metal`, `cpu`, `amd`. It is the file name of every snapshot this
  run writes, and the only backend whose keywords are searched.
- **`keywords`** — the backend's own query list, already written in the prompt. Search it as given;
  do not add, drop or rewrite a query.
- **`model_queries`** — the trending-model queries derived from the store by
  `scripts/query_coverage.py`. Run ALL of them, the same way, in the same last-3-day window: they
  name the models we rank, so a higher figure for one can actually be found (AGENTS.md rule 6o). A
  model no query names is a LOUD gap, so never skip one because it looks unrelated. Each ranked
  model gets **two** queries — one for its throughput (`<id> tokens per second`) and one for its
  **footprint** (`<id> vram ram context weights`) — because a post that answers a throughput query
  can state no VRAM, weight size, context window or engine build, which is exactly why those
  dimension gaps stay open. A footprint figure a post states belongs in its field, never only in
  the prose.
- **`write_raw`** — the exact per-query command for this backend. It is the only write this run
  makes.
- **`AGENTS.md`** — the repository's rules, especially §3 (data source), §3d (no credential in a
  log), §2.3b (additive only) and rule 5 (t/s is always per engine).
- **`skills/gather-data.md`** — the exact scrape technique and query shapes.

## Output

- **One raw snapshot per query**, written immediately after that query:
  `python3 scripts/update_trending.py --write-raw <backend> < payload.json`. Each call writes its
  own `data/raw/<backend>-<UTC>.json` (same-second writes get `-2`, `-3`).
- After EACH query, immediately write only that query's captured models — never collect all queries
  into one big payload, because a reply has a 65536-token cap and a bulk payload loses the whole leg.
- Nothing else. Do not touch `data/models.json`, do not regenerate the README, do not commit, do
  not push, do not merge — the aggregate stage does that.

## Parameters per backend

| backend | what is special about it |
|---|---|
| `nvidia` | NVIDIA/CUDA keywords only: the RTX cards, the low-end 3060 / 4060 / 4060 Ti / 4070 queries, `8gb` / `16gb vram`, and the vendor-specific model queries. |
| `metal` | Apple/Metal keywords only: MLX, Apple Silicon, MLX-fast, TensorFold, DFlash on MLX. Apple Silicon is judged by **unified memory**, never by a VRAM tier. |
| `cpu` | CPU/embedded/edge keywords only: `llama.cpp` CPU-only, Raspberry Pi, "no gpu cpu". A CPU figure never earns a card tier — it keeps the CPU table. |
| `amd` | AMD/ROCm keywords only, plus the ROCm rules below. |

### The AMD leg's own rules

- **Record the AMD card exactly as posted in `hardware`** (for example `RX 7900 XTX 24GB`,
  `RX 9070 XT 16GB`, `Radeon 8060S / Strix Halo 128GB`) — that is what puts the figure in the ROCm
  table, because AMD is classified by HARDWARE, never by engine name (AGENTS.md rule 6).
- **Keep the engine name as registered** (`llama.cpp`, `Ollama`, `vLLM`, `SGLang`, `Strata` …) and
  **put the API (ROCm, HIP, Vulkan) in `quant`, never in the engine name.** A pseudo-engine such as
  `llama.cpp (Vulkan)` or `vLLM (ROCm)` splits one engine's figures across names and is refused.
- **Record generation/decode t/s only**, and **never prompt-processing or prefill t/s**.
- **Skip datacenter Instinct (MI300/MI355) posts** — the headline scope is 8–48 GB consumer and
  workstation cards, and a datacenter figure is never presented as what a card owner can buy.

## Rules

### The mirror is lightbrd.com, and the request shape is fixed

`POST https://api.firecrawl.dev/v1/scrape` with the header
`Authorization: Bearer ${FIRECRAWL_API_KEY}`, where `${FIRECRAWL_API_KEY}` is the NAME of the
environment variable: read its VALUE from the environment BY NAME at call time and put it in that
header — never print, echo or write the value anywhere. The body is
`{"url":"https://lightbrd.com/search?f=tweets&q=<urlencoded>","formats":["markdown"]}`, built for
the query you are running. Search lightbrd.com and nothing else — not x.com directly (bot-walled)
and not Nitter (mostly dead).

### Make the call from the TERMINAL tool, never `execute_code`

Hermes strips provider credentials from its terminal tool and keeps `execute_code`'s child
environment keyless: every variable whose name carries a secret substring is dropped from that child
process and the `_HERMES_FORCE_<NAME>` form is never unwrapped there. So **every Firecrawl call MUST
be made from the TERMINAL tool** — a `curl` command, or a `python3` script you run through the
terminal (`python3 scripts/update_trending.py` reads the key in its own process). **Never make it from `execute_code`**: a Python `urllib`/`requests` call there sends an **EMPTY Authorization
header** and the query dies with **HTTP 401** while the key is set in your shell (issue #362). **A
401 is a blocker to report**, never a reason to hunt for a key and never a reason to write an export
line.

### One query at a time, ranked by interactions then t/s

Scrape a query, extract its models, write that snapshot, then move on. Record the engine, the model,
the hardware, the quant and the figure. Last-3-day window: an older post is not this refresh's data.

### `tps` is a clean number

No embedded text or comments — context like `DFlash spec-decode` belongs in `quant`/`hardware`.
Generation/decode t/s only, never prompt-processing or prefill. A bare figure with no engine is not
a valid entry (rule 5).

### The engine rule

The `engine` field MUST name an inference runtime or server that loads the weights (`llama.cpp`,
`MLX`, `vLLM`, `Ollama` …) AND MUST be the engine the post ACTUALLY NAMES; never guess or manufacture
one. If a post states a t/s but names no engine at all, SKIP that measurement — record the model, not
the figure: a t/s with no engine is not a valid entry, and a made-up engine reds the whole refresh
because an engine with no repo can never be registered. A model name, a vendor name or a
quantization is NEVER an engine: a post about `Nvidia/Qwen3.8-Flash-Next-FP4-Local` running `NVFP4`
names a MODEL and a QUANT — those go in the model/`hf` and `quant` fields, and tokens like
`Nvidia/Qwen3.8-Flash-Next-FP4-Local`, `NVFP4` or `FP4-Local` must never be written as the engine.
Harnesses are not engines: harnesses, agent frameworks, plugins, chat apps, UIs and benchmarks are
NOT engines — if a post only names one of those, record the runtime it uses instead, or skip the
measurement. Use engine names exactly as registered in `data/models.json`. If the post runs a fork
or custom build of an engine (for example the PrismML `llama.cpp` fork that Ternary Bonsai 2
requires), record the engine exactly as that fork is named in the engines registry of
`data/models.json`.

For an engine that is not registered yet, add `engine_repo` = its
`https://github.com/<owner>/<repo>` URL as given in or linked from the post; if the post names the
engine but **links no repo**, run ONE Firecrawl web search for the engine name plus github and record
the repo only when its name matches the engine and the **page resolves**; never invent or guess a
URL.

### The `hf` id is looked up, never guessed

A model's `hf` (and every `formats[].hf`) MUST be the canonical `owner/repo` id
confirmed to resolve — look it up with the authenticated Hugging Face API
(`https://huggingface.co/api/models?search=<name>`) or `hf search models <name>`
before you write it. Read `HF_TOKEN` from the environment BY NAME and never
print, echo or write the value. A plausible `owner/<the model's own name>` is
not a lookup: `Qwen/Qwopus3.6-35B-A3B-Coder-MTP` 404s because Qwen never
published it (the real id was `Jackrong/Qwopus3.6-35B-A3B-Coder-MTP-GGUF`). If
the lookup cannot confirm the id, leave `hf` out and say so; `--write-raw`
refuses an unverified id with a loud warning, so the refresh PR stays green and
the gap is visible in this leg's log.

### The five model dimensions

MODEL DIMENSIONS — before writing each model, check the post for these five and record every one it
STATES: RAM / unified memory → `system_ram_min` (e.g. `16GB`); model weight footprint → `weight_gb`
(e.g. `5.95GB Q4_K_M`); context window → `context_tokens` (e.g. `131072` or `128K`); experts streamed
from storage → `storage_offload` (e.g. `640GB NVMe`); minimum engine build or flags →
`engine_min_version` (e.g. `b6xxx`, `--n-gpu-layers 99`). A figure the post names belongs in its
field, NOT only in the prose/`why` text.

ALSO record these on the MEASUREMENT itself when the post gives them for THAT run, because one
model's quants fit different cards: the quant's weight footprint → `weight_gb` on the measurement,
the context it ran with → `context_tokens` on the measurement, the RAM it needed → `system_ram_min`
on the measurement, experts streamed from storage → `storage_offload` on the measurement, and the
engine build or flags THAT run needed → `engine_min_version` on the measurement (a minimum build is
a property of the engine that produced the figure, not of the model). **Copy only a figure the post
gives: never guess, derive or invent one.**

### `source_post` is the post itself, with its counters

Set `source_post` to the exact post URL `https://lightbrd.com/<user>/status/<id>` — **never the bare
mirror URL or a profile page** — and copy that post's **likes, comments, reshares and views as
integers** onto the same measurement. A placeholder URL or missing counts scores the minimum 1 in
`score_7d`, so the ranking degrades to a post count.

### Never fabricate, never remove, never print the key

- **Never fabricate.** A figure must trace to a post you actually read; if it cannot, leave the key
  unset and say so. Never write a snapshot that no real scrape backs.
- **Never remove a model.** Additive only, in the snapshots as in the store (rule 3b).
- **Never print the key, in any spelling**, and never write it into a file, a snapshot or a summary
  — AGENTS.md rule 3d: a value found in a log is rotated, not excused.
