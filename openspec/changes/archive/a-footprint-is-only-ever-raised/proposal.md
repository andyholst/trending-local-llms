# Proposal: a-footprint-is-only-ever-raised

Issue: #530 (measured: PR #529 red — `captured ['5.95GB']` missing while the store said `5.93GB`)

## Why

`merge_engines` filled a per-measurement dimension **only when the row had none**:

```python
if row.get(k) in (None, "", [], {}):
    row[k] = coerce_additive(member.get(k))
```

§2.3b says a value may only be **raised**, never shrunk. "Never overwritten" is stricter than the
rule and wrong in the other direction: it also forbids raising, so the first figure that ever landed
for a run is pinned for ever — and when the representative row is the one carrying a *smaller*
figure, the merge silently **shrinks** it.

Both directions were measured on one post (`qvac/status/2107139441425014846`, "5.95GB ternary"):
the store row carried `5.93GB` and refused the later `5.95GB`; and merging a `5.95GB` store row with
an incoming `5.13GB` row produced `5.13GB`. `weight_gb` is what the card-fit tables publish as the
budget a run needs, so an understated footprint is a published lie that passes every other gate.

## What Changes

- **`_raised_dimension(stored, incoming)`**: two comparables (a GB figure on either side) → the
  **larger** wins (`5.95GB` beats `5.93GB`; `950MB` never beats `1.2GB`); an unstated side is filled
  from the other; a text dimension (`engine_min_version`, prose `storage_offload`) is never replaced
  by a different spelling, because "later" is not evidence that a version or a medium changed.
- **`merge_engines` uses it for every `MEASUREMENT_DIMENSION_FIELDS` entry**, and never stores a
  `None` (an unstated dimension stays absent rather than becoming a null).
- **The store row for that post is corrected to `5.95GB`** — a raise with the post as provenance, one
  line, not a rewrite.
- **Tests**: five checks driving the REAL `merge_engines` — raise, order-independence, never-shrink,
  adopt-when-empty, never-invent.

## Impact

`scripts/update_trending.py`, `data/models.json` (one value), `tests/test_7day_aggregation.py`,
`OPENSPEC.md`.

## Not covered

- **The refresh PR that surfaced it (#529)** keeps its own copy of the data; the next refresh (or a
  rebase of that branch) carries the corrected figure. This change fixes the RULE, so no future
  refresh can pin or shrink a footprint again.
