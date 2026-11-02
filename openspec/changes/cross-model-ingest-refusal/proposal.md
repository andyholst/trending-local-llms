# Cross-model duplicate attribution: an ingest-time refusal, reusing the #695 allow-list

**Issue:** [#702](https://github.com/andyholst/trending-local-llms/issues/702)
**Capability:** `cross-model-ingest-refusal`

## Why

The misattribution class of issue #693 — one source post's t/s copied onto a
second model the post never measured — was caught at INGEST only when the
copied row's own text NAMES a different model (`misattributed_measurement_reason`
refuses on `named_models_in_text`). The three #693 rows do not name a model in
their text, so today there is **no write-time refusal** for the copy class: a
future re-capture that re-attributes a number is merged into the store
silently, surfaced only post-merge by the report-only
`same_post_cross_model_duplicates` scan and the allow-list `pytest` gate.

The #458/#468 fabricated-engine and text-named-misattribution seams refuse at
the exact seam where the value would enter the store. This change gives the
copy class the SAME seam: a raw measurement whose `(engine, tps, hardware,
source_post)` already exists on a different, already-merged model id is refused
loudly before it merges, unless the pair is a documented allow-list entry. The
allow-list's single source of truth (`update_trending.CROSS_MODEL_ALLOW_LIST`)
is shared by the ingest-time refusal and the #695 post-merge gate, so the two
gates never disagree.

Non-breaking and additive: a refused row is excluded and the rest of the
snapshot still merges (the existing seam behavior); no schema/data/workflow
change; the report-only scan stays report-only for history.

## Delivery

- `scripts/update_trending.py`:
  - `CROSS_MODEL_ALLOW_LIST` — the single-source allow-list (moved verbatim from
    the #695 test; 11 legitimate same-family/same-benchmark tuples).
  - `_cross_model_identity()` — the `(engine, tps, hardware, source_post)` key,
    exactly `validate.same_post_cross_model_duplicates`' key.
  - `cross_model_carriers(store)` — the model ids that ALREADY carry each tuple.
  - `refuse_cross_model_duplicate_measurements(model, carriers)` — splits a
    raw measurement into (kept, refused): a tuple already on a different model
    id is refused unless allow-listed (and it is never the established owner).
  - wired into `ingest_raw_snapshots()` beside the fabricated/misattributed seams.
- `tests/test_cross_model_attribution.py` — imports the shared
  `CROSS_MODEL_ALLOW_LIST` (no copy-paste divergence) and adds tests that call
  the REAL refusal logic on the real store + a real `ingest_raw_snapshots` E2E.
