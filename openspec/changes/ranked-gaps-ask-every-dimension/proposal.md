# Ranked gaps ask every dimension (issue #460)

## Why

Issue #414 gave every ranked model **two** queries — a throughput query and a
footprint query — so a ranked model could no longer be "captured but with no
footprint data" unseen. But the footprint suffix asks for four things
(`vram ram context weights`) while `scripts/data_gap_analysis.py` **ranks five**
dimensions. `storage_offload` was missing on **59 models** and
`engine_min_version` on **35** (measured on `data/models.json` at the base
commit) — asked by NO query in any leg. For those two dimensions, "no such
measurement exists" and "we never looked" are still identical, which is exactly
the blindness issue #264 removed for models and #414 described for the ranked
dimensions. The gap analysis itself cannot close them (they are acquisition
gaps), and the search cannot be expected to surface what it was never asked to
find.

## What Changes

- `MODEL_FOOTPRINT_SUFFIX` gains the two words the missing dimensions need:
  `vram ram context weights offload engine version`.
- `DIMENSION_ASK_TOKENS` + `dimensions_not_asked()` in `update_trending.py`
  pin the suffix to the ONE dimension list (`data_gap_analysis.DIMENSIONS`):
  every ranked dimension must be asked by a token in the footprint query, and a
  new dimension with no token reports itself as unasked instead of slipping
  through.
- `make query-coverage` FAILS (exit 1, loud, named) when a ranked dimension is
  asked by no query, and its `--json` carries `dimensions_missing`.
- The search contract (`skills/gather-data.md`, `.hermes/skills/data-search`)
  names the five things the footprint query asks, so a leg asked "offload" and
  "engine version" knows to capture them into the optional per-measurement
  keys (`storage_offload`, `engine_min_version`) when a post states them.
- AGENTS.md §6o and the §8 guard row carry the rule (rule 3c: this PR changes
  the §6o wording and the §8 row — review-required).

## Impact

- `scripts/update_trending.py`, `scripts/query_coverage.py`
- `skills/gather-data.md`, `.hermes/skills/data-search/SKILL.md`
- `AGENTS.md` §6o + §8 row; `README.md` (template half of §How collected)
- `tests/test_query_coverage.py` (pinned strings + the dimension test)
- No data is added, removed or shrunk (rule 3b intact: the store shape already
  declares both keys as optional measurement fields — only the QUESTIONS widen).

## Not covered

- Re-scraping the 59/35 gaps for the PAST (the next refresh searches are the
  ones newly asking; a backfill is the gap chain's decision, not this change).
- `vram_tier` semantics (a store-level requirement, not a query dimension).
