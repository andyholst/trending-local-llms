# Proposal: data-gap-measurement-dimensions

Issue: #376 — `data-gap: storage_offload (38 models)`

## Why

`make data-gaps` names, as its first line, that "every item below is real data the
search sees and the contract drops or leaves unstructured". For the requirement
dimensions (`weight_gb`, `context_tokens`, `system_ram_min`, `storage_offload`,
`engine_min_version`) a measured part of that sentence is wrong in the other
direction: the value is captured on a MEASUREMENT in `data/raw/*.json` (the record
of a real `…/status/<id>` post), the contracts declare the key OPTIONAL on a
measurement, and the store still does not hold it.

Measured on this tree: 21 measurement cells carry a structured dimension in a raw
snapshot but the matching store measurement is missing it — e.g.
`qwen3.8-27b`'s `llama.cpp` run of 2026-09-16 states `14.6GB IQ4_XS` weights,
`64000` context and `16GB` system RAM in
`data/raw/nvidia-20261019-003834.json`, while the same measurement in
`data/models.json` carries none of the three.

The cause is `scripts/update_trending.py::merge_engines`: a concordant group
collapses to ONE representative row picked by engagement weight, and the row is
`dict(primary)` — every dimension key a non-representative group member carries is
dropped. It can also drop a value the STORE already held when a higher-engagement
incoming row wins. That is a silent loss of real data, exactly the additive-only
rule (AGENTS.md §2.3b) forbids.

## What Changes

- **`merge_engines` fills the representative row's dimension keys from the other
  members of its group, fill-only.** A key the representative already holds is
  never overwritten; a key no member holds is never invented. This makes the
  merge preserve `weight_gb` / `context_tokens` / `system_ram_min` /
  `storage_offload` / `engine_min_version` on both paths (existing store row and
  incoming raw row).
- **The 21 unambiguous captured cells are backfilled into
  `data/models.json`** (8 models), copying the text the raw snapshot holds
  verbatim. Cells where two raw legs captured DIFFERENT values for the same
  measurement are left unset rather than guessed.
- **`tests/test_measurement_footprint.py` drives the real ingest** with an existing
  store row that wins the group as representative and an incoming row carrying the
  dimensions, and with the reverse order (an incoming row must not drop a value the
  store already held).
- **`tests/test_data_gap_analysis.py` proves traceability**: every measurement-level
  dimension value in the real store appears verbatim in that model's captured raw
  text, and a coverage floor keeps the backfill from silently disappearing.

Additive only: no key is removed or renamed, no required list changes, no existing
value is shrunk (`check_no_value_loss` keeps it that way).

## Impact

`scripts/update_trending.py` (`merge_engines`), `data/models.json` (the backfilled
measurement cells), `README.md` (regenerated: the card-fit tables read a
measurement's `weight_gb`), two test modules, this OpenSpec change and the
regenerated `OPENSPEC.md` index. No make target, stage, pipeline job, image or
script is added or renamed, so `ARCHITECTURE.md` is unchanged (rule 6h).

## Not covered

- **A model-level value for every gap.** Most of the 38 models missing
  `storage_offload` have no captured post that states one (a dense model that fits
  in VRAM/RAM has no storage offload to record); the prior change
  `data-gap-storage-offload` (#364) established this and left them unset on
  purpose. Inventing a value is the one failure this stage must never make.
- **A value the store already held.** When two raw legs captured different wording
  for one measurement (e.g. `qwen3.8-27b`'s 2026-10-14 context as `8192` in one leg
  and `65536` in another), the merge only fills an ABSENT key and never overwrites —
  resolving which capture is right is not this change's judgement; `findings.md`
  records the disagreement.
- **Counting a measurement-level value as "captured" in `analyse()`.** The ranked
  list is model-level by design (it ranks model rows); changing its counting rule is
  a separate judgement and belongs in its own change (rule 6g).
- **Deriving a dimension from engine defaults** (e.g. "Strata ⇒ experts on SSD"): the
  field is what the post states, never a registry inference.
