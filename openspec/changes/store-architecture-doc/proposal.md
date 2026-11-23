# Proposal: store-architecture-doc

Issue: #1395

## Why

`ARCHITECTURE.md` §2 still draws the pre-#689 flat store — `data/models.json` with an inline `engines[]` list — while the tree ships a catalog × measurements × posts split. Measured on `d4096735`: `data/models.json` holds 120 catalog models and **0** inline `engines[]`; `data/measurements.json` holds 120 model keys / 611 measurement rows; `data/posts.json` holds 382 posts keyed by `source_post`. A reader cannot tell where a figure lives.

## What Changes

- `ARCHITECTURE.md` §2 corrected to the shipped three-file store and bounded by a new `<!-- arch:dataflow -->` anchor.
- New `docs/store.md`: the longer walkthrough — shape, budgets, the flatten seam and the per-run footprint variants.
- `scripts/architecture_check.py::store_file_findings`: the §2 data-flow region must NAME all three shipped store files (names only, never prose); `tests/test_architecture.py` gains the fixture anchor and four tests.
- `AGENTS.md` §7b wording + rule-3c note and one §8 regression row (rule 3c review-required, declared on #1395; carried as a blocked box in this headless leg).

## Impact

Documentation plus one deterministic guard extension. No data, contract, schema, API, table, workflow or cron change. The `AGENTS.md` rows are review-required under rule 3c.

## Not covered

- `data/models.json`, `data/measurements.json`, `data/posts.json`, the generated README, any contract JSON, a workflow, a cron, the lane profile (#1396 slice C).
