# Captured gap cells trace by measurement identity, never by raw row name

Issue: #411

## Why

Issue #411 measured the defect on real snapshots: a footprint (weights / context /
minimum-engine build) was captured in a post that the search cited under **one** raw
model id, while the measured figure itself merged onto a **different** store row (a
hardware variant). `captured_text` keys the capture only by `resolve_model_mapping` of
the raw ROW, so the variant's captured bucket was empty and its cell read as an
ACQUISITION gap ("only a new search can close it") although the post that states the
figure already sits in `data/raw/`. Every acquisition/ingest decision built on such a
cell is wrong: the honest class is INGEST. The #660 report's `cross_model_measurements`
count showed the shape live today: 1,259 raw engine rows, 993 of them citing posts a
different store model also cites — the same-post-cited-by-two-ids class #411 names.

## What Changes

- `data_gap_analysis.captured_text` gains a **measurement-identity join**: a captured
  ENGINE row's field text is also contributed to the bucket of the store row that
  carries that exact `(engine, tps, hardware, source_post)` tuple — the ONE key
  `update_trending._cross_model_identity` defines (rule 6d; the same identity #702's
  ingest refusal and `validate.same_post_cross_model_duplicates` read) — but only when
  exactly ONE store row carries it.
- A tuple carried by TWO store rows is a **joint** figure: ownership is ambiguous and
  the text is copied to NEITHER (the #458/#651 rule that a joint figure belongs to no
  single row). A tuple carried by NO store row is attributed to nothing.
- The join is analysis-only: no measurement is moved between store rows; the store and
  raw snapshots are never mutated. The acquisition/ingest split stays a disjoint
  partition of the missing set.

## Impact

- Affected: `scripts/data_gap_analysis.py` (`captured_text` + new
  `_join_measurement_identity`), `tests/test_data_gap_analysis.py` (2 new tests).
- Pipeline: `make data-gaps` / `make data-gap-issue` decisions become honest for the
  variant class — an ingest job is filed as ingest work, not a redundant re-search.
- **Not covered:** structural ingest itself (writing `weight_gb`/`context_tokens`/…
  onto rows — the standing ingest issues); any change to `merge_engines`, the store, or
  the raw snapshots; never copying text across rows for a JOINT measurement remains, as
  the #411 done-when already required and the echoed/quoted fixtures already pin.

## PR
PR: #910
