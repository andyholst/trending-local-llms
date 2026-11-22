# Proposal: vetted-performance-1252

Issue: #1252
PR: #1255

## Why

The README 🔥 tables are buzz-first; measured high-t/s models are hidden in 🕑. Readers
cannot see the fastest vetted setup per VRAM band with its engine/quant/source evidence.

## What Changes

- `scripts/vetted_performance.py` + `make vetted-performance`: read-only top measured t/s
  per VRAM band, deduplicated by source post + engine + hardware, with quant/date/posts_7d
  and README band. Rows without a source post are excluded as UNVETTED unless explicitly
  requested. No store write, no `sort_models` change, no type reassignment.
- ARCHITECTURE rows, Makefile target, regression suite.

## Capabilities

### New Capabilities
- `vetted-performance-view`: evidence-attached per-VRAM leaderboard, read-only.

### Modified Capabilities
- (none)

## Impact

No shipped value edits; owner still rules in #1252 on the threshold and on whether this
view may outrank buzz inside band 0.
