# Proposal: trending-for-your-card

Issue: #349 — `feat(readme): the trending list for YOUR card — VRAM-tiered trending tables, low end (8–24 GB) first`

## Why

The headline list is supposed to answer a **card owner's** question — with 8–48 GB of VRAM, what is
*tending* that I can actually run? — and it did not. Two things broke it:

1. **The scope gate read SKUs, never a class of machine.** `in_scope()` recognised datacenter parts by
   model family (`b300`, `h100`, `mi300` …) and by total VRAM, but a hardware string that names no card
   at all — the shipped store's `datacenter GPUs, 512 concurrent requests` — passed both tests
   (`hardware_vram_gb()` returns `None`, which the gate admits). Measured on `master` (`829cc7e`):
   Qwen3.8-27B's **28,340 t/s** AGGREGATE figure from a 512-request SGLang cluster earned
   `speed +11.5`, headed the ❤️ Most loved row and was printed as its "CUDA t/s (best)" cell, while
   the fastest figure on a card a reader can buy was 500 t/s on an RTX 5090 (+5.7).
2. **The trending list was one global ranking.** It ranked by a score whose speed term could come from
   any in-scope card, so a 128 GB Mac Studio at 300 t/s and a 32 GB RTX 5090 at 500 t/s competed in the
   same column, and the ranking the reader with a 16 GB laptop needs did not exist at all.

## What Changes

- **`update_trending.in_scope()`** refuses a hardware string that names a datacenter CLASS
  (`datacenter`, `data centre` …) exactly as it already refuses a datacenter SKU. This is the measured
  28,340 t/s shape; the figure stays in its backend table and in the ranking's buzz, it just stops
  earning speed or a "best" cell.
- **`update_trending.tier_trend()` / `tier_trending_rows()`** — a **tier-local trend**: the model's
  7-day buzz unchanged, plus a speed bonus earned only by a measurement that **ran on a card ≤ the
  tier** (reusing `tier_measurements()` / `fits_tier()`, never a second fit rule). One derivation,
  read by the renderer and by the validator.
- **`render_readme()`** gains `## 🔥 Trending for your card — low end first` as the FIRST section:
  a selector line and one table per tier (`Up to 8 GB` … `Up to 48 GB`), ranked by the tier-local
  trend, with `No limit` (the existing ❤️ Most loved list) linked below it. Every tier table names
  the measurement that earned the speed bonus and the model's least VRAM need.
- **Most-loved VRAM cell** now names the **card the headline figure ran on** next to the least VRAM
  the weights need, so a 5090-sourced number cannot be read as "fits my 16 GB laptop".
- **`validate.check_card_trending`** (`readme` stage) fails when the section is missing or out of
  order, when a tier's rows differ from `tier_trending_rows()`, when a tier is not ranked by its own
  local trend, when a speed term in a tier table came from a card above the tier, or when an empty
  tier is not a named collection gap.
- **`tests/test_trending_for_your_card.py`** — the 28,340 t/s shape, the tier-local speed bonus, the
  no-bigger-card rule, the section order and the validator falsified against a mutated README, plus
  the real store and the real README (no fixture-only claim).

## Not covered

- **Tiers above 48 GB (64/128/256/512).** The fit ladder is VRAM-card evidence, and beyond 48 GB the
  evidence is unified memory or datacenter hardware that `in_scope()` deliberately excludes, so those
  tiers need their own ladder. Filed as its own finding (rule 6g) instead of shipping four empty tables.
- **Re-scoring the store's cached trend fields.** `make merge` recomputes them, and this change runs it;
  no value is invented, removed or shrunk (rule 3b allows a raised/computed value to move).
- **Crawl changes.** The search legs already ask for the 8–48 GB cards (`skills/gather-data.md`).
