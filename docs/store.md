# The store: catalog × measurements × posts

The repository keeps its data in THREE files under `data/`, not one. This page
explains the shape of each, the budgets that bound them, the seam that splices
them back together for readers, and why a single model carries several t/s
figures. `ARCHITECTURE.md` §2 has the short version; this is the walkthrough.

## Why three files

Before issue #689 everything lived in one flat `data/models.json`: each model row
carried an inline `engines[]` list, and every measurement row repeated the
engagement counters of its source post. That duplicated one like count once per
citing row, so correcting a post meant editing every copy. The store now splits
the facts that change independently:

- a model's **identity** and metadata,
- the **measurements** reported about it,
- the **engagement** of the posts that report them.

Engagement is published ONCE per post. A corrected like count edits one entry in
`data/posts.json` and every model row that cited the post sees it.

## The three files

### `data/models.json` — the catalog

Top-level keys `generated_utc`, `note`, `engines` (the engine registry: engine →
repo URL and backend) and `models` (a LIST of rows). A model row carries `id`,
`name`, `full_name`, `hf`, `license`, `params`, `type`, `vram_tier`, `vram_min`,
`backends`, `supported_engines`, `formats`, `engine_aliases`,
`measurement_model_aliases`, `why`, `engagement` and `last_seen`. It carries **no
inline `engines[]` measurements**. Shape: `data/model_contract.json`, documented
in `data/MODEL_CONTRACT.md`.

### `data/measurements.json` — where a figure lives

A JSON object keyed by `model_id` → a list of measurement rows. A row is:

```json
{
  "engine": "llama.cpp",
  "tps": "91",
  "hardware": "RTX 4060 Ti 16GB",
  "quant": "Q4_K_M",
  "date": "2026-11-20",
  "source_post": "https://lightbrd.com/<user>/status/<id>"
}
```

The engine is always named, and the hardware and quant always ride along: a bare
t/s is not a valid entry (AGENTS.md rule 5).

### `data/posts.json` — engagement once per post

A JSON object keyed by the `source_post` URL → `{date, likes, comments, reshares,
views, interactions}`. A post URL is always the post itself
(`https://lightbrd.com/<user>/status/<id>`), never a profile or a bare mirror
link. Counters may only GROW, so re-observing a post raises its stored count and
never shrinks it.

## Budgets

`scripts/update_trending.py` owns the three windows:

- `SEARCH_WINDOW_DAYS = 3` — each search leg looks back three days, so a post is
  captured even if the mirror is quiet for a day.
- `TRENDING_WINDOW_DAYS = 7` — the "trending" band. Buzz sums the distinct posts
  dated within the last seven days; a model with no post in the window is not
  trending.
- `RETENTION_DAYS = 30` — the "recent" band, and the prune horizon for post
  entries. Retention never deletes a MODEL: a model with no new post simply
  sorts further down (recent → stale) and stays in the store and the README,
  marked with its measurement date.

## The flatten seam

Readers never open the three files themselves. `load_store()`
(`scripts/update_trending.py`) reads all three and `flatten_store(catalog,
measurements, posts)` reconstructs the pre-#689 flat shape: for every model it
builds an `engines[]` list from `data/measurements.json` and splices each row's
counters (`likes`, `comments`, `reshares`, `views`, `interactions`) from
`data/posts.json`. `render_readme`, `sort_models`, ingest and validation all
operate on that flat in-memory store, so the split changed no reader code.

`split_store(store)` is the inverse, run on merge: it strips the counters off
each row into `data/posts.json` (taking the MAX across rows that cite the same
post, because counters may only grow) and removes `engines[]` from the catalog.
A legacy flat store with no split files loads unchanged, so old snapshots stay
readable.

## Per-run footprint variants

One model usually has SEVERAL t/s figures, and that is correct: the same weights
run at different speeds on different cards, quants and context windows. Each
measurement row may therefore carry its own OPTIONAL footprint:

| key | meaning |
|---|---|
| `weight_gb` | Weight footprint per format + quant the post states (e.g. `5.95GB Q4_K_M`). The budget a run needs before any context is allocated. |
| `context_tokens` | Context window the post states (e.g. `131072`, `128K`). The KV cache scales with it and consumes RAM and VRAM alike. |
| `system_ram_min` | System RAM / unified-memory requirement the post states (e.g. `16GB`). The CPU and Metal tables are RAM-bound and partial offload keeps layers + KV cache in system RAM. |
| `storage_offload` | Storage-offload requirement (e.g. `640GB NVMe, experts on SSD`). MoE engines stream experts from storage. |
| `engine_min_version` | Engine minimum version / flags the post states (e.g. `llama.cpp b6xxx, --n-gpu-layers 99`). Many figures only reproduce on a specific build. |

These are per-RUN values, stated by the post the row cites — never derived from
VRAM and never invented. The card-fit tables and the speed bonus read the best
IN-SCOPE figure for a model, and the model-level copy of a footprint must match a
value captured FOR that model or carry the canonical `(est)` marker.

## Where a number comes from

A figure traces through all three files: the model row names the model, the
measurement row in `data/measurements.json` names the engine, t/s, hardware,
quant and date, and the `source_post` URL resolves to the counters in
`data/posts.json`. Every value must trace to a real X post; an unverifiable one
is marked `(est)` or refused, never invented.
