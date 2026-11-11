# Proposal: source-post-figure-readback

Issue: #531 — "data: nothing re-reads a measurement's source_post, so a stored figure can contradict the post it cites and every gate stays green".

## Why

`data/models.json` carries a `source_post` on every measurement, and `data/raw/*.json` holds
the captured text of those posts. Nothing compares the two: a stored figure can contradict the
post it cites, and every existing gate stays green.

Measured (found while fixing #530): `bonsai-2-27b` / `llama.cpp (PrismML fork)` /
`source_post …/qvac/status/2107139441425014846` carried `weight_gb: "5.93GB"` while its own
`quant` reads `5.95GB ternary (PTQ1_0), SDK runtime` and all three raw captures of that post
state `5.95GB`. It survived weeks of green CI and was caught only when a NEW capture stated the
figure as a structured field.

`scripts/validate.py` checks presence, links, schema, table shape and value loss — none of them
re-reads the post. A dimension the tables publish (`weight_gb` drives the card-fit "what fits
your card" rows) is user-facing advice: a wrong figure is worse than a missing one (a missing
one is labelled `not stated`; a wrong one is presented as measured).

## What Changes

- **`scripts/validate.py`** gains a report-only scan, `check_source_post_readback`, that for
  every measurement whose `source_post` appears in `data/raw/*` re-derives the stated footprint
  dimension values (`weight_gb`, `context_tokens`, `system_ram_min`, `storage_offload`,
  `engine_min_version`) from the captured text and flags a stored value that appears in NEITHER
  the capture's structured fields NOR the captured post text. Report-only FIRST (so it cannot
  red a refresh on a parser miss), the same pattern as `check_duplicate_runs` (#459):
  precision is measured on the store as it stands, and a later change can turn it into a gate.
  Registered under the existing `data` stage, so it reaches CI through `make validate` without
  a new target, stage, workflow or image (rule 6d).
- **Tests:** `tests/test_source_post_readback.py` (new) exercises the REAL read against a real
  temp raw snapshot tree — no mock of the business logic: a stored value the capture states is
  kept, one the capture nowhere states is flagged, a measurement whose post is not captured is
  skipped, and the figure-token matching handles spacing (`5.95 GB` vs `5.95GB`).

## Impact

`scripts/validate.py`, `tests/test_source_post_readback.py`, this OpenSpec change, the
regenerated `OPENSPEC.md` and an AGENTS.md §8 row. No new make target, stage, workflow or
image (`ARCHITECTURE.md` unchanged, rule 6h).

## Not covered

- **The scanned store is NOT repaired by this change.** Report-only: the 22 unsupported values
  currently measured on the store (mostly engine-build prose the capture does not restate, plus
  a few genuine footprint mismatches) are surfaced every `make validate`, but nothing is
  rewritten and no PR goes red for history the scan cannot judge. Fixing the rows is a separate
  data change once the report's precision has had time to be read.
- **A value the raw capture itself dropped** (the post states a figure the search never
  recorded) reads as "unsupported by the capture" and is reported, not silently passed — the
  issue's contract is the captured text, and on partial captures that over-reports rather than
  under-reports, which is exactly why the scan is report-only.
