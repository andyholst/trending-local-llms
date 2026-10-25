# A closed gap dimension is judged, not re-filed

**Issue:** [#491](https://github.com/andyholst/trending-local-llms/issues/491)
**Capability:** `data-gap-analysis`

## Why

The gap chain's only productive outcome is `close` — and each close is re-opened by the next
morning's filing. Of the twelve `storage_offload` issues since 2026-10-15, five were CLOSED by the
implementer verdict (it read the thread and closed with evidence) and the same dimension was filed
again on the next refresh, because only the individual ISSUE was closed. The chain files a DATA gap
as an IMPLEMENTATION issue, so `implement` is never the right verdict; nothing recorded "this
dimension was already judged not implementable".

## What Changes

- **`scripts/data_gap_analysis.py`** — `already_filed()` now returns the OPEN issue *and* the CLOSED
  ones with their `closedAt`. A closed issue carrying the signature is a **judgement about the
  dimensions it named**, so the baseline records `judged: {dim: <closedAt>}`.
- `judged_dimensions()` reads that map and keeps a dimension out of the filed set while the
  judgement is younger than **`JUDGED_DAYS` (21)**; after that the claim is re-examined.
- `dimension_of()` maps a signature entry (`missing:storage_offload`) to its dimension.
- When every dimension in the signature is inside its window the run **files nothing** and says so
  per dimension on stderr — no silent skip.
- `write_baseline()` persists the `judged` map beside `as_of`/`signature`.

## Impact

One judgement survives the next refresh instead of being re-derived every morning. A dimension the
signature no longer carries is untouched, and a genuinely new dimension still files immediately.

## Not covered (out of scope)

- The window is a fixed 21 days; a dimension whose gap WORSENS (twice the models) is still
  suppressed inside it. Filed as a finding, with the "shape changed" trigger it needs.
- Verdicts recorded before this change are not back-filled: the first close after it lands is the
  first judgement remembered. Filed as a finding.
