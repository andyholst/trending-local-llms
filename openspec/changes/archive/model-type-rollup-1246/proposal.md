# Proposal: model-type-rollup-1246

Issue: #1246 (companion to the pending owner ruling #1235)
PR: #1247

## Why

The 13 raw `type` labels split MoE models into two buckets and mix formats/quantization with architectures. Grouping by raw label misreports type-level trending; editing the shipped store to fix it would breach rule 3b while #1235 is un-ruled.

## What Changes

- `scripts/model_type_rollup.py` + `make model-type-report`: a derived, read-only `type_group` join across models.json and measurements.json.
- Unknown labels reported, never silently bucketed; alias joins honoured.
- ARCHITECTURE rows, §8 row, injected-fixture suite.

## Capabilities

### New Capabilities
- `derived-type-rollup`: read-only, deterministic type-level trending aggregation.

### Modified Capabilities
- (none)

## Impact

No store data, no workflow, no credentials; no closing keyword for #1235.
