# Proposal: vram-min-prose

Issue: #431 — `tech-debt: a prose vram_min is published as its first number (32GB GPU + system RAM -> 32GB)`

## Why

`vram_need()` reads `vram_min` through `_gb_value()`, which returns the FIRST number in the
string. One store row states a **split** requirement —
`"system RAM holds the expert set (32GB GPU + system RAM)"` (`deepseek-v4-flash`) — so the
most-loved VRAM cell published `**32GB**<br><sub>stated by the source</sub>`: the GPU half of
a requirement whose whole point is that the experts stream from system RAM. To a card owner
that reads "fits a 32 GB card", which the source does not promise. Nothing reported the
free-text value, so the truncation was invisible.

## What Changes

- **`_SPLIT_REQUIREMENT(raw)`** — true only when the value names a GPU capacity (`gpu`/`vram`,
  **not negated**) *and* RAM. `"16GB RAM"` (a unified-memory statement) and
  `"8GB RAM (no GPU)"` (a CPU statement, measured in the first draft of this change) stay
  plain capacities.
- **`vram_need()` returns `("32GB + system RAM", "declared")`** for such a value, so both
  halves are named and the evidence stays `declared`.
- **`README.md` re-rendered** with `make render-readme` (#195): one cell.
- **`validate.check_vram_min_vocabulary`** (report only, `data` stage) — prints every
  `vram_min` that is prose rather than a plain capacity, so a human can structure it; it
  never fails. It names two values in the store today.
- **Tests**: the split names both halves, a plain RAM capacity is not split, `no GPU` is not
  a split, and the report names the prose values.

Verified RED against the pre-change function (the split check fails — the row renders `32GB`)
and GREEN after (`79 passed, 0 failed` in `test_card_fit.py`, 15 checks in the vocabulary
module).

## Impact

`scripts/update_trending.py` (one predicate + three lines), `scripts/validate.py` (one
report-only check + registration), `README.md` (one cell), `tests/test_card_fit.py`,
`tests/test_vram_tier_vocabulary.py`, this OpenSpec change and the regenerated
`OPENSPEC.md`. No new target, stage or image (`ARCHITECTURE.md` unchanged).

## Not covered

- **Structuring the store's `vram_min`** — replacing prose with a number is a data decision
  (what number describes "32GB + system RAM"?) and the report is what makes it visible.
- **The other dimensions' backfills** (#213/#370) — each remains its own evidence-carrying
  change.
