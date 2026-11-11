# Proposal: engagement-value-fidelity

Issue: #699 — `ENH: #698 reader switch silently re-resolves engagement`

## Why

PR #698 (the #697 switch-over, merged) resolved every measurement row's engagement from
the canonical `data/posts.json` at load time, which is the intended GWT2 behavior and the
#411/#650/#463/#525 fix. But its OpenSpec proposal overstated the side-effect as
`README.md byte-identical`, and the shipped guards (`check_no_value_loss` /
`check_split_flatten`) only fail on a SUM **drop** — they are blind to upward drift, so
they cannot prove that a row's engagement equals the canonical post entry **value-for-value**.

This change corrects both:

1. The proposal's false "byte-identical README" claim is removed. The proposal now
   discloses that engagement-derived buzz/trend lines are **re-resolved** from canonical
   `posts.json` per GWT2, so a corrected post entry raises every referencing row and the
   rendered README is regenerated accordingly — it is not "unchanged", it is
   **re-resolved to the canonical value**.
2. A **value-fidelity guard** is added: for every (model, engine) pair derived through
   `flatten_store`, each of the five engagement counters must equal `posts[source_post]`
   **exactly**. The non-shrink guard is kept alongside it (it protects the #463/#525/
   #411/#650 loss classes against a future drop).

## What Changes

- **`tests/test_measurements_split.py`** — NEW guard `test_flatten_engagement_equals_posts_value_for_value`:
  for every measurement row materialised by `flatten_store(catalog, measurements, posts)`,
  assert `row[c] == posts[source_post][c]` for each counter in
  `_MEASUREMENT_COUNTERS`, for every row that has a canonical post entry (a row with no post
  entry resolves to 0). This is the primary engagement-resolution contract; the non-shrink
  guard still protects against drops.
- **`openspec/changes/measurement-store-normalized/proposal.md`** — the line claiming
  `README.md byte-identical` is corrected to disclose that engagement-derived buzz/trend
  lines are regenerated from canonical `posts.json` (the intended GWT2 consequence).
- **`openspec/changes/measurement-store-normalized/specs/catalog-measurements/spec.md`** —
  the scenario titled "render via load_store is byte-identical" is retitled to reflect that
  t/s band and card-fit rows match while engagement-influenced buzz/trend lines are
  re-resolved from `posts.json` (GWT2).
- **`README.md`** — regenerated to the re-resolved engagement values (the honest artifact);
  the only substantive difference vs `master` is the re-resolved buzz/trend lines plus the
  freshness timestamp.

## Impact

Small, non-breaking, additive: a new test function + two OpenSpec text corrections + the
regenerated README. No reader, schema, store-shape or guard behavior changes beyond the
newly-added value-fidelity check. Everything lands green under `make lint`, `make test`,
`make validate` (readme/data/schema) and `make openspec-check`.
