# A stated figure no post supports is its own class — a capture job, never an ingest one

**Issue:** [#470](https://github.com/andyholst/trending-local-llms/issues/470)
**Capability:** `data-gap-analysis`

## Why

`make data-gaps` classified every model whose requirement figure lived only in free text
as `unstructured` — "stated in prose only, an ingest job" — and on the shipped store that
label was wrong for one of them. `gemma-4-12b` states `256K ctx.` in `why`, its
measurements cite a real post that states **no** context window, and no captured post does
either: there is nothing an ingest change can point a structured `context_tokens` at. The
only outcomes of that "ingest job" are inventing the attribution (which
`tests/test_data_gap_analysis.py::test_structured_dimensions_trace_to_a_real_post` forbids)
or deleting the prose (which rule 3b forbids). So the gap was reported correctly and could
never close — the defect is in CAPTURE, and the report was sending triage to the wrong work.

Measured on the tree at `202bb4e` (`python3 scripts/data_gap_analysis.py`): of the 5 models
in `unstructured:context_tokens`, 4 have a captured post that states a window (real ingest
work) and 1 — `gemma-4-12b` — has none.

## What Changes

- **`scripts/data_gap_analysis.py`** — the ONE implementation of the class (rule 6d):
  - `analyse()` gains `untraceable`: a dimension's figure is stated in the model's own
    `why`/`quant`/`hardware`, and NO captured post states it. The model moves out of
    `unstructured` (that stays "a captured post states it too — an ingest job").
  - `stated_untraceable(store)` and `unattributed_figures(store)` are the reusable halves —
    the report and the validator call the SAME functions, so they cannot disagree.
  - `render()` gains `## Stated but untraceable (no post behind the figure — a capture
    job)`; `issue_body()` gains the same section; the ranked line's `_gap_kind()` names the
    class as its own kind (`capture gap`), and the per-dimension finding says how many.
  - The class is **not** a signature entry: a signature entry files an issue, and one issue
    per untraceable sentence would re-file the same dimension on every refresh (the #472
    churn) while only a new CAPTURE can retire it.
- **`scripts/validate.py`** — `check_untraceable_figures`, registered in the `data` stage
  (`make validate`, `validate-data`, `validate-mapped`): it FAILS a model whose prose states
  a requirement figure while NO measurement on the row cites a real `…/status/<id>` post
  (the shipped store holds none, so history stays green) and REPORTS the stated-but-
  uncaptured class, which is history the store cannot repair without breaking rule 3b.
- **`.hermes/skills/data-search/SKILL.md`** — the search prompt stops the shape being
  written: a requirement figure lives on the measurement whose post states it, never only
  in the model-level `why`/`quant`, and a figure no post states is not written at all.
- **`AGENTS.md`** §8 — the guard row for the new validator check and the class.

## Impact

The report gains a section and a class; one model (`gemma-4-12b`) moves from the ingest
list to the capture list. No data key or value is removed or shrunk (rule 3b), no signature
entry is added (so no new issue is filed by the next refresh), and nothing in the ranking or
the README changes. `make validate` gains a failure mode that no current row trips.

## Not covered (out of scope)

- **Repairing `gemma-4-12b`**: the prose is history and the figure has no post, so the only
  honest repair is a refresh that captures the post stating it. That is data work for a
  search run, not a code change — and deleting the sentence would violate additive-only.
- **Making the class a filed issue**: it is a capture job by construction, and the filer's
  job is to file structurable gaps; filing it would re-open the churn #472 ended.
- **Backfilling the other four `unstructured` models**: they are genuine ingest work and
  stay reported as such; this change does not implement them.
