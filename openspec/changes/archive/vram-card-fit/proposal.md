# A card owner can see what fits THEIR VRAM — and the low end comes first

**Issue:** [#337](https://github.com/andyholst/trending-local-llms/issues/337)
**Capability:** `card-fit`

## Why

The index exists to answer one question: *"I own N GB of VRAM — which open-weight model gives me the most t/s, on which engine, at which quant?"* The README answered a different one. Measured against the live store (46 models, 213 measurements):

- The most-loved **VRAM** cell is `vram_tier`, a free-string CATEGORY, not a requirement. It disagreed with the model's own `vram_min` for **20 of 46** models, sat *below* the smallest card any of its measurements had run on for **17**, and for two models (`Qwen3.5 9B` tier `16GB` / min `32GB`, `DeepSeek-V4-Flash`) the category was smaller than the model's own stated minimum. A card owner read "16GB" on Qwen3.8-27B and clicked through to a figure measured on a 32 GB card.
- The per-backend **best** cells used `best_measurement()`, the *unscoped* best, while the trend score uses `best_in_scope()` — so the answer for a card owner could be a datacenter figure (`Qwen3.8-Flash-Next 125B`: 685 t/s on `4x GB300`, datacenter) or a bare `B300` (21,000 t/s) — the same defect issue **#260** records for a `2x32 GB` rig under an "8-48 GB" column.
- **`b300` was missing from `_DATACENTER_HW`**, so a measurement reading `single NVIDIA B300 GPU (datacenter)` passed `hardware_vram_gb()` as `None` and `in_scope()` as `True`: `LFM2.5-24B-A2B` earned `speed +11` from it and ranked 3rd, against AGENTS.md §5 ("datacenter parts never earn speed").
- There was **no way to ask** "what fits 8/12/16 GB": the four backend tables sort by t/s across every card size at once, and nothing states the smallest card a model was ever run on.
- The low end is also a **collection** gap, not only a presentation one: **30 of 46** models have no CUDA/ROCm measurement on a card ≤ 24 GB, and **37 of 46** none ≤ 16 GB. Measurements by card: ≤8 GB **5**, ≤12 GB **9**, ≤16 GB **11**, vs ≤24 GB **35** and >48 GB/unknown **30** — because every card query in the CUDA leg named a 3090/4090/5090 and the AMD leg named 7900 XTX/9070 XT.

## What Changes

- **`scripts/update_trending.py`** — the ONE implementation (rule 6d) of the fit:
  - `_DATACENTER_HW` gains **`b300`**, so a bare B300 is treated like every other datacenter part.
  - The evidence ladder `fits_tier()` / `weights_gb()` / `card_memory_gb()` / `tier_measurements()` / `tier_rows()`: a tier row is **proved** by a run on a card ≤ tier (`ran-on`), or is `weights-only` when only the stated weight footprint fits a smaller tier **and** the run's own card is known — labelled, never sold as a fit. A datacenter measurement **never** places a model in a card tier (`in_scope` gate).
  - `vram_need()`: the least VRAM needed, evidence-tagged — `vram_min` (`declared`) → `vram_tier` (`tier`) → smallest card it ran on (`measured-on`) → `unknown`. The coarse tier is never published as a requirement.
  - `LOW_END_TIERS_GB = (8, 12, 16, 24)` — a **gaming laptop** — and `CARD_TIERS_GB = (8, 12, 16, 24, 32, 48)`.
  - Renderer: a new **`## 🖥️ Pick your card — what fits your VRAM`** section with an anchor index and one block per tier (model · best t/s that fits · backend · engine · hardware · quant · date · evidence), an empty tier rendered as a named **collection gap**, the most-loved per-backend best cell now the **in-scope** best, and the most-loved VRAM cell now `vram_need()` with its evidence.
  - `SEARCH_GROUPS` gains the gaming-PC cards (3060 / 4060 / 4060 Ti 16 GB / 4070, `8gb vram …`, `16gb vram …`; AMD: 7600 / 6600 / 9060 XT, `radeon 8gb vram …`), kept identical to the `_search-*` prompts.
- **`data/model_contract.json` + `data/search_contract.json`** — the measurement item gains OPTIONAL `weight_gb`, `context_tokens`, `system_ram_min`, `storage_offload` (additive, never `required`, rule 3b): one model's quants fit different cards, so the footprint belongs to the measurement that produced the t/s.
- **`data/MODEL_CONTRACT.md`** — the prose for those keys.
- **`Makefile`** — `DIM_ASK` asks for the per-measurement footprint; the four search prompts carry the low-end card queries; `_test` runs `tests/test_card_fit.py`.
- **`scripts/smoke_search.py`** — the smoke keyword lists follow the prompts (they must match verbatim).
- **`scripts/validate.py`** — `check_card_tables` (registered in the `readme` stage, reachable from `_validate-readme` and `make validate`): the section and its anchor index exist, every model the ONE derivation places in a tier is listed there with an evidence tag, sorted by t/s descending, and an empty tier says "collection gap". `check_readme_measurements` now expects the **in-scope** best and the least-VRAM cell.
- **`tests/test_card_fit.py`** (in `make _test`) — the ladder, the datacenter gate, the Apple/CPU exclusion, `vram_need`, the rendered section, and the guard falsified by a dropped row.
- **`AGENTS.md`** (§5b layout, §5 the scope gate the displayed cells use, §4 the new optional keys, §8 the guard row), **`skills/gather-data.md`** (per-measurement dimensions + the low-end cards), **`OPENSPEC.md`**.

## Impact

The README gains one section and its two most-loved cells change meaning; the trending list's **order is untouched** (`buzz + speed`, rule 4) — the low end is prioritised by what the cells *show* and by the tier tables beside them, never by re-sorting the trend. Data is unchanged except for the search prompts and the contracts; no stored key or value is removed or shrunk (rule 3b). No network. A model that only ever ran on a big card stays in the ranking and in the backend tables — it just stops being presented as the answer for an 8 GB card.

## Not covered (out of scope — separate issues)

- The **inference-server support table** ("what models does each engine demonstrably run, with coverage") — issue **#338**; it consumes this change's fit truth and must not re-implement it.
- A real **filter UI** (a GitHub Pages page with a dropdown): markdown cannot filter, so phase 2 gets its own change and its own pipeline job.
- Catching up the low-end **data** for models that only have a big-card figure: this change adds the queries and the per-measurement fields; the figures arrive with the next refreshes, and an empty tier says so loudly in the meantime.
