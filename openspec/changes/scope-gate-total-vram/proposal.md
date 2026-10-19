# Proposal: scope-gate-total-vram

Issue: #260 — `data: a per-backend 'Most loved' cell can show a measurement the scope gate excludes`

## Why

The scope gate exists so a card owner is never shown a figure measured on hardware
they cannot buy (`in_scope()`: ≤ 48 GB consumer/workstation, Apple, CPU — AGENTS.md §5).
Two spellings of the same fact defeat it:

- **A pool total is not read.** `hardware_vram_gb()` takes the FIRST `NN GB` in the
  string, so `Radeon Pro V620 32GB x8 (256GB total, …)` reads as **32 GB** — the
  per-card size — and the 256 GB cluster lands inside the 8–48 GB band.
- **A trailing multiplier is not read.** The multiplier regex requires the count
  BEFORE the `x` (`2x RTX 3090`); the mirror image (`32GB x8`, `24GB x2`) is ignored,
  so `32GB x8` also reads as 32.

Measured on `master` `cc06fcf`: the most-loved ROCm cell for
`qwen3.8-flash-next-125b` showed **100 t/s on "Radeon Pro V620 32GB x8 (256GB
total, user-built homelab cluster)"** under a column labelled `ROCm — AMD GPUs
(8–48 GB)` — a figure the score itself refuses, because `in_scope()` returned `True`
for it. The in-scope ROCm figure for that model is 60 t/s on an RX 9070 XT 16GB.

## What Changes

- **`hardware_vram_gb()` reads an explicit pool total first** (`<n> GB total` wins over
  any per-card size) and **applies a multiplier that trails the size** (`32GB x8` → 256,
  `24GB x2` → 48). The existing `2x 3090` path is unchanged.
- **`_DATACENTER_HW` gains AMD's datacenter V-series** (`v620`, `v520`, `v340`). A
  V620 is a cloud-gaming/VDI part, never a card a reader buys — and the family is
  listed, not one spelling (the #337 rule). Radeon Pro **W**-series (W7900/W7800) are
  workstation cards and stay in scope.
- **`README.md` regenerated** from the store at its own `generated_utc` (no merge, no
  snapshot, no timestamp bump): the 125B ROCm cell now shows 60 t/s on an RX 9070 XT,
  and the engine matrix cell follows.
- **`tests/test_trend_score.py`** extends `test_vram_parsing` with both spellings and
  adds `test_a_multi_card_pool_is_never_a_card_you_can_buy`, which asserts the pool is
  out of scope, that a single V620 is out, that a W7900 stays IN, and that
  `best_in_scope()` picks 58 over the 100 on the cluster.

Verified RED against the pre-change `scripts/update_trending.py` (6 checks fail:
`32GB x8` → 32, `24GB x2` → 24, the pool in scope, the single V620 in scope, and
`best_in_scope()` returning the cluster row).

## Impact

`scripts/update_trending.py` (`_DATACENTER_HW`, `hardware_vram_gb`),
`README.md` (regenerated), `tests/test_trend_score.py`, this OpenSpec change and the
regenerated `OPENSPEC.md`. No make target, stage, pipeline job or image changes
(`ARCHITECTURE.md` unchanged, rule 6h).

## Not covered

- **Re-classifying every existing datacenter pool in the store.** The gate now rejects
  them, but a measurement's `hardware` text is the search agent's wording; auditing all
  48 models for other pool phrasings (`4x …`, `N× …` with a unicode times sign, a
  rack's aggregate) is separate work and would need its own issue if a case is found.
- **`vram_min` / `vram_tier` drift** (#341, #343) — the card-fit view derives its answer
  from measurements, not those fields, so this change does not touch them.
