# Proposal: acquisition-gap-needs-a-search

Issue: tech-debt `ranked-gaps-need-new-search-data` (filed while implementing #395, surfaced by PR #410)

## Why

The ranked dimension gaps (`context_tokens` 66, `engine_min_version` 59, `weight_gb` 49,
`system_ram_min` 39, `storage_offload` 34 on this tree) are read as ingest work — the store
cannot hold a figure the search acquired. Measured against the captured snapshots, that is
false for almost every one of them:

    $ python3 - <<'…'   # re-merges/scan of every data/raw/*.json against the store
    system_ram_min:      missing=39  captured-states-it=0
    weight_gb:           missing=49  captured-states-it=1
    context_tokens:      missing=66  captured-states-it=5
    storage_offload:     missing=34  captured-states-it=0
    engine_min_version:  missing=59  captured-states-it=0

Every missing model HAS captured rows (112 of 112 models), and those rows state no such
figure for it. So the store is not dropping captured data — the data was never captured. The
report called all of it "missing", the filing inherited that word, and the issue is re-filed
unchanged on every refresh for a gap only a NEW SEARCH can close.

The other half of the diagnosis: the searches DO name the ranked models (issue #264,
`QUERY_TOP_N` / `derived_queries`), but the derived query is `<id> tokens per second` — it
asks for a throughput figure and nothing about the footprint. A post that answers it can
legitimately state no VRAM, weights, context window or engine build.

## What Changes

- **A footprint query per ranked model** (`scripts/update_trending.py`):
  `footprint_query(m)` = `<id> vram ram context weights`, and
  `footprint_queries(store, top_n)` returns one per top-`QUERY_TOP_N` trending model.
  `all_search_queries()` appends BOTH the t/s query and the footprint query to every leg, so
  each of the four `_search-<backend>` prompts asks for the ranked models' footprints as well
  as their throughput. `derived_queries()` keeps its meaning (one t/s query per model).
- **The analysis separates an ACQUISITION gap from an INGEST gap**
  (`scripts/data_gap_analysis.py`): a missing dimension is now classified per model against
  the model's own CAPTURED text in `data/raw/*.json` (resolved to the store id by the ONE
  resolver, `update_trending.resolve_model_mapping`):
  * **not stated by any captured post** — no captured snapshot states the figure for that
    model: only a new search can close it (`not_captured`);
  * **stated in prose only** — a captured post (or the store's own prose) names it and the
    store has no structured value: that is ingest/structuring work (`unstructured` /
    `captured`), unchanged in meaning and now reported beside the acquisition count.
  The report and the filed issue say which is which, per dimension, with the model ids.
- **Wording follows the measurement**: the ranked line reads
  `**context_tokens** — 66 model(s): 61 not stated by any captured post (acquisition gap),
  5 stated in prose only (ingest gap)`, and a dedicated section lists the acquisition ids.
  The issue-triggering SIGNATURE is unchanged (`missing:<dim>` / `unstructured:<dim>`), so
  this does not re-file every dimension as a new gap set (issue #472's churn).
- **Tests** (`tests/test_query_coverage.py`, `tests/test_data_gap_analysis.py`): the footprint
  query names the model and asks for the footprint terms; every leg carries it; the split is
  a disjoint union of `missing` on the real store; a model whose capture states nothing is
  `not_captured` and one whose capture states it is not; and the render/issue body both say
  "not stated by any captured post".
- **AGENTS.md** rule 6o gains the footprint query, §8 names the new guards; `README.md` is
  regenerated from the store template in `update_trending.py`; `skills/gather-data.md` says
  what the footprint queries are for.

## Impact

`scripts/update_trending.py` (two helpers + one list), `scripts/query_coverage.py` (the
`--queries` output and the report), `scripts/data_gap_analysis.py` (the classification and its
render), `Makefile` (one sentence in the four search prompts), the two test modules,
`AGENTS.md`, `README.md` (regenerated), `skills/gather-data.md`, this change and the
regenerated `OPENSPEC.md`. No make target, stage, pipeline job, image or script is added or
renamed, so `ARCHITECTURE.md` is unchanged (rule 6h).

## Not covered

- **Filling any dimension.** This changes what the searches ask for and what the report says;
  it invents nothing. A model whose post states no footprint stays unset (rule 2/§2.3b).
- **The store's own `unstructured` detector** — it is the ingest half and keeps its current
  patterns; only the ACQUISITION half is new.
- **`vram_tier` / `vram_min`**, which are already structured and out of the dimension set.
- **A backfill from the existing snapshots.** Measured above: there is nothing to backfill —
  0–5 models per dimension state the figure, and those are already reported as
  `unstructured` (each has its own evidence-carrying change).
