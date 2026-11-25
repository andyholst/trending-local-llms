# Proposal: query-coverage-report-named-queries

Issue: #1693
PR: #1698

## Why

`scripts/query_coverage.py::prompt_queries(store)` drops every composed query that
names no row of the store (issue #1688, PR #1692), so `--queries` — exactly what the
`_search-<backend>` prompts append — now reflects only searchable queries. But the
default coverage REPORT was left reading the RAW compositions directly:
`report()` counts `update_trending.derived_queries` / `footprint_queries` /
`aged_derived_queries` / `aged_footprint_queries` and builds its `full_queries` from
`update_trending.all_search_queries()`, none of which apply that filter. On a store
carrying a ranked row with an empty `id`, `trending_models()` keeps the row (only the
coverage GUARD is meant to flag it), so the report still prints vacuous empty-id
queries. Measured on PR #1692's branch with a synthetic two-row store (one named, one
nameless): the report said `2 derived (throughput) + 2 footprint ... added to EACH leg
= 51 sent in total`, while `--queries` emitted only `named-model tokens per second,
named-model vram ram context weights offload engine version` (35 curated + 2 = 37 per
leg). A reader trusting the report overestimates what each search leg sends, and the
two surfaces of the SAME module disagree.

## What Changes

- Add ONE filtered seam in `scripts/query_coverage.py` (`_named_queries`) that applies
  the SAME predicate `update_trending.query_names_model` `prompt_queries()` uses, and
  route both consumers through it: `prompt_queries()` keeps its behaviour, and
  `report()` computes its derived/footprint/aged counts and its `sent in total` line
  from the filtered sets, so the report and `--queries` cannot disagree.
- Add a RED-first regression test pinning report/`--queries` agreement on a store
  carrying an unnamed ranked row: the reported `sent in total` equals
  `len(SEARCH_GROUPS) * (len(curated) + len(prompt_queries(...)))`, and the reported
  per-category counts equal the filtered set sizes.

## Impact

No data, contract, format, make target, workflow or image change, and no `AGENTS.md`
rule change. `make query-coverage`'s DECISION is unchanged (exit 1 when a ranked model
no query names, exit 2 on `--top 0`), the guard's exit codes are untouched, and on the
shipped store — where every ranked row has a usable id — the report is byte-identical.

## Not covered

- No change to `update_trending.derived_queries` / `all_search_queries` / the guard.
- No change to the `--json` payload shape beyond making its lists agree with the
  filtered seam.
- No change to how an unnamed row is FLAGGED (that stays the exit-1 gap the analysis
  reports).
- No refresh of `data/models.json`.
