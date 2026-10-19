# Proposal: data-gap-acquired-footprint-capture

Issue: #395 — `data-gap: storage_offload (40 models)`

## Why

`make data-gaps` names, as its first line, that "every item below is real data the
search sees and the contract drops or leaves unstructured". The contract half is
already true (`data/model_contract.json` declares `weight_gb`, `context_tokens`,
`system_ram_min`, `storage_offload` and `engine_min_version` OPTIONAL on a model
**and** on a measurement — `"Contract gaps: none"` in the filed issue). The other
half is measured false in one specific place: a per-run footprint the search DID
capture is sometimes absent from the store measurement it belongs to.

Measured on the store BEFORE this change, comparing every captured dimension cell
in `data/raw/*.json` with the store measurement carrying the same
`(model, source_post, engine)`:

    $ python3 - <<'…'   # see tests/test_data_gap_analysis.py::test_a_captured…
    pre-change stored cells checked: 65 lost: 3
      qwen3.8-flash-next-125b/Strata/system_ram_min on 2111251412973699533 (captured
        ['64GB (developer recommendation; tested on 128GB)',
         '64GB recommended (128GB DDR4-2400 tested)'])
      qwen3.8-27b/oMLX/engine_min_version on 2105743490864869554 (captured ['oMLX 0.7.0'])
      qwen3.8-27b/mlx-serve/engine_min_version on 2105743490864869554 (captured ['mlx-serve 26.10.1, --no-mtp'])

Three real cells the refresh acquired — the RTX 3090 Strata run's system-RAM
requirement and two engine builds — were lost to the store while the analysis
keeps reporting the dimension as "not captured". That is a silent loss of real
data, which AGENTS.md §2.3b forbids ("Loss is a defect, not a simplification"),
and it is exactly the gap the issue's own words describe.

The same comparison also shows WHY most of the 40 models stay missing: the
captured posts state no such figure for them, and the ones that do are captured
under a DIFFERENT model (measured: one post's `4221` context sits under
`qwen3.8-27b` in one leg and `bonsai-2-27b` in another), so copying it across
models would be a fabrication. A model whose post states nothing stays unset.

## What Changes

- **`data/models.json` gains four captured cells**, each on the store
  measurement whose `(model, source_post, engine)` the snapshot recorded it for,
  quoting the captured text verbatim: `qwen3.8-flash-next-125b`'s Strata row gains
  `system_ram_min: "64GB recommended (128GB DDR4-2400 tested)"`,
  `qwen3.8-27b`'s oMLX row and mlx-serve row gain their `engine_min_version`
  (`"oMLX 0.7.0"`, `"mlx-serve 26.10.1, --no-mtp"`), and `bonsai-2-2b`'s MLX row
  gains its `weight_gb` (`"0.43GB ternary"`) — the per-run footprint the card-fit
  tables read (issue #337). Additive only: no existing key is removed or renamed
  and no existing value is shrunk (`check_no_value_loss` keeps it that way).
- **A guard on the loss itself**, in `tests/test_data_gap_analysis.py`:
  `test_a_captured_measurement_footprint_is_never_lost_from_the_store` recomputes
  the comparison over the REAL store and the REAL raw snapshots and fails when a
  captured cell is missing from its store measurement. It FAILS on the pre-change
  store (3 lost cells, measured above) and passes after the backfill; it also
  proves the rule bites by stripping a captured value from an in-memory copy and
  requiring the guard to report it.
- **Per-dimension coverage floors** in
  `test_measurement_dimension_coverage_can_never_shrink`: the total floor rises
  from 43 to 46 measurements carrying a structured dimension, plus a floor PER
  DIMENSION (`weight_gb` 26, `context_tokens` 18, `system_ram_min` 24,
  `storage_offload` 2, `engine_min_version` 14) so one dimension's capture cannot
  be dropped while the total still passes on the other four.
- **`README.md` is regenerated** from the store (the timestamp line: the
  dimension values are not rendered by `render_readme`), and the refresh snapshot
  is written by `scripts/update_trending.py`.

Nothing about the *capability* changes: the contracts already declare every key
OPTIONAL on both levels, and ingest already merges them
(`MEASUREMENT_DIMENSION_FIELDS`, `merge_engines`' fill-only pass).

## Impact

`data/models.json` (three captured cells), `data/snapshots/trending-*.json` (the
regenerated snapshot), `tests/test_data_gap_analysis.py` (the new guard, the
per-dimension floors, its `main()`), the OpenSpec change and the regenerated
`OPENSPEC.md` index. No make target, stage, pipeline job, image or script is added
or renamed, so `ARCHITECTURE.md` is unchanged (rule 6h) — verified by
`make architecture-check`. AGENTS.md §8 gains the new guard in the
`tests/test_data_gap_analysis.py` row (rule 6c).

## Not covered

- **A model-level `storage_offload` for the 40 models the issue's title ranks.**
  Measured in this tree: scanning every text field of every captured snapshot for
  a storage medium (`ssd`/`nvme`/`flash`/`disk`/`hdd`) co-occurring with an
  offload or streaming verb finds NO model that states one and lacks the field —
  the matches are the ten models that already carry it. The remaining hits are
  CPU/RAM offload ("26 MoE layers offloaded to the CPU") or a weight size
  ("14.6GB on disk"), not a storage offload. A full re-merge of every raw snapshot
  into the store (`ingest_raw_snapshots(store, since=None)`) adds no model-level
  value for any of the five dimensions: the figures are not in the captured posts.
  Inventing them is the one failure this stage must never make (§2.3b, §3.2).
- **The other eight ranked gaps** (`context_tokens`, `weight_gb`,
  `unstructured:weight_gb`, `engine_min_version`, `system_ram_min`,
  `unstructured:storage_offload`, `unstructured:context_tokens`,
  `unstructured:system_ram_min`). They are separate dimensions with separate
  evidence; the cells whose capture is a judgement call are recorded in
  `findings.md` as their own work (rule 6g), never folded in here.
- **Cross-model evidence.** A captured value recorded under model A is never
  copied onto model B, even when the `source_post` matches (measured: 5 such
  pairs). `findings.md` files that misattribution as its own issue.
- **Counting a measurement-level value as "captured" in `analyse()`.** The ranked
  list is model-level by design; the deferral recorded by
  `openspec/changes/data-gap-measurement-dimensions` still stands and is filed in
  `findings.md`.
