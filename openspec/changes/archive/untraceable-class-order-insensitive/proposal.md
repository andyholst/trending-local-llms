# Proposal: untraceable-class-order-insensitive

Issue: #1826
PR: #1830

## Why

The refresh rebuilds `data/models.json` from new raw snapshots, which can reorder
the catalog without changing any figure. `tests/test_data_gap_analysis.py:504`
compared the real store's `untraceable:context_tokens` to an order-fixed list, so
the reordered store (qwen before gemma) failed the run even though the classifier
was correct and `unstructured:context_tokens` was empty. The detail
`[['qwen-3.6-27b','gemma-4-12b']]` is the `check()` helper's wrapper around a
reversed list, not an untraceable-to-unstructured class move.

## What Changes

- `tests/test_data_gap_analysis.py:504` compares
  `set(report["untraceable"]["context_tokens"])` to `{"gemma-4-12b", "qwen-3.6-27b"}`
  — exact membership is still asserted, only order is ignored.
- Lines 505-506 (the class-separation assertions) and every `scripts/` file stay
  byte-identical. No second classifier, no data/README/workflow/schema change.

## Impact

- `tests/test_data_gap_analysis.py` — one line.
- No product-code, data, README, workflow or schema change; non-breaking.

## Not covered

- The regenerated store itself: it lands from the existing refresh pipeline.
- #1827 and #1828 (sibling fixture and closure issues) — separate dispatches.
