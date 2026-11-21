# Proposal: positive-more-count

Issue: #1219
PR: #1221

## Why

The per-VRAM 🔥 tables rendered `+-1 more measured at this size` — a negative count — because
two copies of the render code computed `sum(ran-on) - 1` even when the shown row was not
classified ran-on by the same tier seam (count 0 → −1). 29 such labels were measured in the
shipped README, including the 32 GB / 48 GB Strix Halo and EXL3 rows. Negative "more" counts
are invented data (rule 2) in the user-facing trending tables.

## What Changes

- ONE `_other_ran_on_count(cands, shown, shown_ev)` in scripts/update_trending.py, used by
  both the card tables and the above-48-GB tables; counts OTHER ran-on rows by measurement
  identity (engine/tps/date/source_post), never a blind −1.
- README.md re-rendered from the store: 29 negative labels gone, 116 positive labels kept.
- tests/test_tier_more_count.py (8 checks incl. RED on the old expression).

## Impact

Specs: readme-render. Code: scripts/update_trending.py, README.md, test file.
No store data changes.

## Verification

New suite 8/8, engine-figure-alignment 32/0, validate --only data QA PASSED, lint green.