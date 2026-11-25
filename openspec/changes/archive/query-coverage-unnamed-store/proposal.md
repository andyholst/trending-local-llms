# Proposal: query-coverage-unnamed-store

Issue: #1688
PR: #1692

## Why

`scripts/query_coverage.py::prompt_queries(store)` composes the TOP-N trending pair
and the QUERY_AGED_N aged pair and is non-empty whenever the store has any searchable
row. But the trending half is built from `update_trending.trending_models()`, which
KEEPS a row whose `id` is empty, while `aged_models()` deliberately excludes such rows.
So a store whose only ranked rows have no usable id yields
`prompt_queries() == [" tokens per second", " vram ram context weights offload engine version"]`:
non-empty, so `test_the_prompts_and_the_guard_are_wired`'s anti-tautology assertion
(`bool(sent)`) passes, while NO returned query names any model
(`UT.query_names_model(q, m)` is False for every `q`). The wiring check therefore
holds while the derivation names nothing — the exact "an empty key must never match
every query, or the guard is vacuous" shape rule 6o forbids, reintroduced one level up
in the TEST's expectation. Measured on PR #1684 head `ccaa9c78` (now merged as
`4b669822`): `prompt_queries(all-nameless)` non-empty, `all(q in expanded_prompt)` True,
`query_names_model` False for every model.

## What Changes

- `prompt_queries()` drops every composed query that names NO row of the store,
  decided through the ONE predicate `update_trending.query_names_model`. A query
  built from an empty `id` names nothing, so it cannot reach a search prompt.
- `test_the_prompts_and_the_guard_are_wired` strengthens its anti-vacuity assertion:
  the live derivation must be non-empty AND at least one returned query must name a
  real row (`any(query_names_model(q, m))`), not merely be non-empty.
- Add `test_an_all_nameless_store_yields_no_vacuous_query`, a RED-first regression
  test over the all-nameless store: it asserts the UNFILTERED composition was
  non-empty and named nothing (the measured defect) and that `prompt_queries()`
  emits nothing.

## Impact

No data, contract, format, make target, workflow or image change, and no `AGENTS.md`
rule change. `make query-coverage`'s DECISION is unchanged: exit 1 when a ranked model
no query names, exit 2 on `--top 0`, and the aged sample's exclusion of unusable ids
is untouched. Only queries that name no model stop being emitted; on the shipped store
(120 named rows) `--queries` output is byte-identical.

## Not covered

- No change to `update_trending.trending_models` / `aged_models` / `derived_queries`.
- No change to the coverage guard's exit codes or its report wording.
- No `AGENTS.md` rule change (the module already carries a §8 row).
- No refresh of `data/models.json`.
