# Proposal: cross-model-ingest-date-identity

Issue: #971 — "The ingest-time duplicate refusal still keys on hardware, not date"
PR: #1009

## Why

The ingest-time refusal `refuse_cross_model_duplicate_measurements` (issue #702)
and the report-only scan `same_post_cross_model_duplicates` (issue #693) both key
a duplicate on `(engine, tps, hardware, source_post)`. The post-merge gate
`check_no_duplicate_measurements` (issue #795) keys on `(engine, tps, date,
source_post)` plus the variant-pair signature. A raw capture that re-measures a
figure with a renamed hardware label ("R9700" vs "AMD R9700", same date, same
post) therefore passes ingest under the hardware-keyed identity and is only
caught at validate — a red PR and a fix-loop round per occurrence instead of an
ingest-time skip logged with its reason.

The refusal seam is the cheap place to stop a copy before it enters the store.
It must read the SAME identity the gate reads, from ONE implementation (rule 6d):
a duplicate is the date-stable tuple, not the hardware label.

## What Changes

- `scripts/update_trending.py`: `refuse_cross_model_duplicate_measurements` and
  its carrier-builder `cross_model_carriers` read the (engine, tps, date,
  source_post) same-post signature instead of the hardware-keyed
  `_cross_model_identity`. The carriers map the store by that signature; the
  refusal refuses an incoming measurement whose same-post tuple is already
  carried by a different model id, and keeps the documented allow-list pairs.
- The identity signature lives in ONE place (rule 6d): the shared helper reads
  the same key function `validate.cross_row_duplicate_measurements` uses, so the
  gate and the refusal can never disagree about what a duplicate is.
- `tests/test_cross_model_attribution.py` gains a planted hardware-renamed
  duplicate (same date + post, hardware "R9700" vs "AMD R9700") and proves it is
  refused at ingest, and the existing refusal tests are updated to the
  date-keyed identity.

## Impact

- A hardware-renamed duplicate is refused at ingest in `make test`; the shipped
  store still passes `check_no_duplicate_measurements` and the refusal ball-park
  (`cross_model_carriers` still maps the same allow-listed pairs).
- The report-only hardware-keyed scan (`same_post_cross_model_duplicates`) is
  UNCHANGED — this change only moves the ingest-time refusal seam to the gate's
  identity, not the historical report scan.

## Not covered

- The report-only `same_post_cross_model_duplicates` scan and the #695 gate
  semantics: the #795 gate already keys on date; the report scan stays the
  historical hardware-keyed view for observability.
- Any change to which models are in the store or the allow-list.
