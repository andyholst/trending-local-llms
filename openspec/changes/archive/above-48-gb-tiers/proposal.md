# Above 48 GB: the tiers a card owner cannot buy

**Issue:** [#572](https://github.com/andyholst/trending-local-llms/issues/572)
**Capability:** `card-fit`

## Why

`CARD_TIERS_GB` stops at 48 and `in_scope()` refuses everything above it, so the 64/128/256/512 GB
tiers issue #349 asks for were **empty by construction**: `fits_tier()` returns `None` for an
out-of-scope measurement, and an Apple Silicon or datacenter run has no per-card VRAM to compare
against a tier. Four empty tables would read as "nothing fits" — the exact defect #337 fixed.

## What Changes

- **`HIGH_TIERS_GB = (64, 128, 256, 512)`** with its own ladder, `high_tier_fit()`:
  - evidence is the **run's total memory** (`total_memory_gb`: VRAM with `Nx` multiplied, else the
    largest GB figure the hardware states — the unified memory of `M3 Ultra 512GB`, the RAM of a CPU
    run) or the model's **weight footprint**;
  - `ran-on` = a run whose own total was in (48, tier]; `weights-only` = the weights fit but the
    run's machine does not prove the fit (labelled, never sold as a fit);
  - **a model is placed here only when it NEEDS more than 48 GB** — the model's weight footprint
    exceeds 48 GB. Without that gate an 8B served on a 64 GB Mac mini topped the 64 GB table and
    buried the models that need the machine (measured, first cut of this change).
  - Apple Silicon and CPU measurements are **not** skipped here (unified memory and RAM are exactly
    what these tiers are), unlike the card tiers where they never appear.
- **`weights_gb()` refuses a contradicting footprint** (`WEIGHTS_CONTRADICTION_FACTOR = 10`): a
  measurement's `weight_gb` more than 10× away from the model's own is a mis-ingested row, not
  evidence — measured in the shipped store, where Bonsai 2 9B (2 GB ternary) carried
  `~493GB NVFP4` from a 4× M5 Ultra run and the ladder read it as proof it needs 512 GB.
- **README**: the card section gains an "Above 48 GB" block — what the memory is (unified, multi-GPU,
  datacenter), one table per tier, and a named **collection gap** instead of an empty table.
- **`check_card_tables`** validates both ladders with their OWN row function, so a >48 GB row is
  never checked against the card rule, and reports above-48-GB coverage as report-only.

## Impact

The store's real rows render: 10 models across the four tiers (e.g. Qwen3.8-Flash-Next 125B at
938 t/s on a 128 GB machine), instead of four empty tables.

## Not covered (out of scope)

- Only 41 of 106 models state a weight footprint, so the ladder is as good as the captures — filed as
  a finding and reported by `make validate` on every run.
- The `AGENTS.md` §8 row for this guard is owed (protected file, needs review) — recorded in
  `findings.md` and named in the PR body.
