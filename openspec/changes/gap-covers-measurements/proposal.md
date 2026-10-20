# Proposal: gap-covers-measurements

Issues: #388 (full finding) · #368 (its truncated duplicate)

## Why

`analyse()` built each dimension's missing set from the MODEL row alone:

```python
ids = [m.get("id", "?") for m in models if not m.get(key)]
```

But #337/#376 deliberately moved a run's footprint onto the measurement (`weight_gb`,
`context_tokens`, `system_ram_min`, `storage_offload`, `engine_min_version`), and **both**
contracts declare every such dimension OPTIONAL on a measurement item. A value that lives
only on a measurement was therefore reported `missing:<dimension>:<id>` on every refresh,
with the same data-gap issue filed again and again — #364 then #376 both topped out at
`storage_offload` while the store held the data.

## What Changes

- **`_stated(m, key)`** in `scripts/data_gap_analysis.py` — the one definition of "is this
  dimension captured": true when the model row carries a non-empty value **or** any of its
  measurements does. Used for the `missing` set AND as the skip condition for the free-text
  (`unstructured`) scan, so a measurement-level value is neither `missing` nor
  `unstructured` — which is what the issue's "done when" asks for.
- **`test_a_measurement_level_value_is_captured`** in `tests/test_data_gap_analysis.py`: a
  model whose only `storage_offload` lives on one measurement is not missing, not
  free-text-only, and not in the issue-triggering signature, while a sibling that states it
  nowhere still is.

Verified RED against the pre-change `analyse()` (2 failures — the measured model was still
reported) and GREEN after (`PASSED 127 | FAILED 0`).

## Impact

`scripts/data_gap_analysis.py` (one helper + two call sites), `tests/test_data_gap_analysis.py`
(one test), this OpenSpec change and the regenerated `OPENSPEC.md`. On the real store the
`storage_offload` missing set drops to 39/50 and `engine_min_version` to 20/50 — the
dimensions whose values already live on measurements stop re-filing the same issue. No target,
stage, job or image changes (`ARCHITECTURE.md` unchanged, rule 6h).

## Not covered

- **Backfilling the dimensions that are genuinely absent** (`context_tokens` 31/50,
  `weight_gb` 24/50). This change is about *counting* correctly; the missing figures remain a
  search target.
- **#368's separate closure text.** The finding is one item filed twice (the second body was
  truncated by the #205 defect); both issues close together, each bound to its own keyword.
