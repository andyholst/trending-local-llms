# Proposal: the-owed-section-4-sentence

Issue: [#371](https://github.com/andyholst/trending-local-llms/issues/371)
Capability: `rulebook`

## Why

`AGENTS.md` §4 — the bullet that describes `data/models.json` — names the optional
per-measurement dimensions a measurement may carry:

```
optional `weight_gb`, `context_tokens`, `system_ram_min`, `storage_offload`
```

Four. Both contracts declare **five**: `engine_min_version` sits on the measurement item
(`properties.models.items.properties.engines.items.properties.engine_min_version`) of
`data/model_contract.json` and of `data/search_contract.json`, and on the model row too
(`grep -c engine_min_version` → 2 in each file). The gap chain ranks all five
(`scripts/data_gap_analysis.py::DIMENSIONS`), so the rulebook described a footprint
narrower than the store can hold, and an agent reading §4 had no reason to fill the fifth
dimension the contracts accept.

The finding was filed instead of written because §4 is a protected agent-instruction file:
in a headless bot run an `AGENTS.md` write is gated behind an approval prompt that never
returns — *"Silence is not consent"* (#310). This issue is the separate work item that
carries the exact replacement sentence, so the same class of drift (a guard registered, a
sentence owed, the gap reopening quietly) gets its own reviewed change instead of a
smuggled edit.

## What Changes

- **`AGENTS.md` §4** — the `data/models.json` bullet states the issue's sentence: the five
  optional dimensions, with why the minimum engine build is a per-measurement fact (it
  belongs to the engine that produced the figure), citing `(#337, #371)`. Documentation
  only: the key already exists, is already accepted by both contracts, and is already
  ingested — no rule, stage, job, pipeline contract or behaviour changes.
- **`tests/test_measurement_footprint.py`** — `test_the_rulebook_names_every_measurement_dimension`
  keeps the sentence and the contracts from drifting again, DERIVING both sides instead of
  listing them a second time (rule 6d):
  - the required set is `data_gap_analysis.DIMENSIONS` (the gap chain's own registry);
  - the stored set is each contract's measurement item `properties`;
  - §4's named set is parsed out of the real `AGENTS.md`.
  Every tracked dimension must be named in §4, every name in §4 must be a measurement key a
  contract declares, and every tracked dimension must have a measurement key in both
  contracts. Verified RED on the pre-change `AGENTS.md` (exactly one failure:
  `agents: §4 names the tracked dimension engine_min_version`) and GREEN after.
- **`AGENTS.md` §8** — a row for that guard (rule 6c: a change's guard row lands in the
  same change), naming the measured defect and what the guard catches.

## Impact

`AGENTS.md` (§4 sentence, §8 row), `tests/test_measurement_footprint.py` (one new check),
this OpenSpec change and the regenerated `OPENSPEC.md`. No data value, contract key, make
target, pipeline job, stage, image or script changes; `README.md` is untouched (no data
changed), and `ARCHITECTURE.md` needs no edit (no target, job, image or script moved).

## Not covered

- **The other owed rulebook rows.** §8 still has no row for `tests/test_measurement_footprint.py`
  itself as the footprint guard (`test_a_measurement_footprint_survives_ingest`,
  `test_the_store_still_conforms_to_the_contract`, `test_the_footprint_drives_the_card_fit`,
  `test_the_contract_declares_them_optional`) — the row added here describes only the new
  §4/documentation drift guard. That pre-existing §8 gap is reported in `findings.md`, not
  fixed here (analysis ships issues, never code).
- **Backfilling `engine_min_version` values.** The sentence documents a dimension the store
  MAY hold; filling it for models that never stated one is the gap chain's work
  (`make data-gaps`), and inventing a value is forbidden (rule 2).
- **The `AGENTS.md` §6j/§4/§8 rows other open issues own** — each names its own wording and
  follows in its own change.
