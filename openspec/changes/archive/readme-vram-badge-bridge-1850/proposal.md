# Proposal: readme-vram-badge-bridge-1850

Issue: #1850
PR: #1851

## Why

At the freshly fetched base `c52276e39935adc20c9dd81bd4ec816c2d98d78b`, the "🔥 Trending for your card — low end first" intro promises that a speed bonus is earned only by a measurement on a card of that size or smaller, but never says what the `VRAM` badge means. In the "Up to 8 GB" table, Qwen3.8-27B shows a 12GB badge / "headline on NVIDIA DGX Spark (GB10)" while its tier came from the 4GB "Best t/s that fits" cell — so the row looks misplaced. "🖥️ Pick your card" already explains the tier rule; the trending section needs a bridge.

## What Changes

- Add ONE short sentence to the section intro: the `VRAM` badge is the model's least-needed VRAM and its headline figure's card; the tier and speed bonus come from the card in the "Best t/s that fits" cell; a larger headline card in the badge does not mean the row is misplaced; link to "🖥️ Pick your card" for the tier rule.
- Put the SAME sentence in the generator's hard-coded intro string in `scripts/update_trending.py` (`trending_card_section()`), so `make render-readme` keeps it. This is a prose string literal only — no logic, data, schema, table-shape or behavior change. Measured: with the sentence in README.md alone, a real `make render-readme` deleted it and restored the README byte-for-byte (grep count 1 -> 0); with the template fixed, two consecutive renders are idempotent and the README diff is exactly one paragraph.
- Add this tracked change, `findings/1850.md`, and regenerate `OPENSPEC.md`.

## Impact

Additive prose only. No table row, number, badge, store value, contract, rulebook, workflow or schedule changes. No new test file: the existing render-consistency and card-fit tests are cited as the locking references.

## Not covered

- No data/schema/table-shape change, no engine or renderer behavior change, no second doc, no AGENTS.md / SOUL / SKILL edit, no cron, no Actions schedule, no push to `master` and no hand-merge.
