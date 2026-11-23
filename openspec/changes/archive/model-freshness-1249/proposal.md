# Proposal: model-freshness-1249

Issue: #1249
PR: #1250

## Why

A measured model can be absent from the README 🔥 tables for two very different reasons:
a capture gap (no fresh post) or a rank/band decision. Readers see neither reason.

## What Changes

- `scripts/model_type_rollup.py --model-id <id>` prints a read-only per-model freshness
  audit: newest measurement, days behind the newest store date, in-window vs historical
  row counts, median parsed t/s, engines/architectures, and an explicit VERDICT.
- Tests for stale, current and unknown ids; no store write.

## Capabilities

### New Capabilities
- `model-freshness-audit`: explain a single model's trend-window status with evidence.

### Modified Capabilities
- (none)

## Impact

Read-only; no shipped `type` value reassigned (rule 3b, #1235 pending), no ranker change.
Refs #1234, #1246, #1247.
