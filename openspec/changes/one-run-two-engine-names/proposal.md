# One run counted once

**Issue:** [#459](https://github.com/andyholst/trending-local-llms/issues/459)
**Capability:** `data-integrity`

## Why

`merge_engines` keys a measurement on (engine, hardware, quant), so a **renamed** engine — a
fabricated name, a renamed fork, a fixed typo — appends a second row instead of updating the first.
The backend tables, the engine matrix and the card-fit evidence then count one run twice, and a
reader comparing engines is told two engines did what one did.

Measured: `qwen3.8-flash-next-125b` carries the SAME post, date and **191 t/s** under `vLLM` and
under `FP4-Local` (a quant token — refused by ingest since #458). The shipped store holds **22**
such figures.

## What Changes

- **`validate.duplicate_runs(models)`** — groups a model's measurements by (source_post, date, t/s)
  and returns every group with more than one ENGINE name. A placeholder post, a missing date or a
  missing t/s never identifies a run, so none of them is reported.
- **`check_duplicate_runs`** — **report only** (registered in the `data` stage, so `make validate`,
  `make validate-data` and every refresh print it). It never fails: the history predates the ingest
  refusal and cannot be repaired by reding every PR.
- The output says what it is — a **renamed engine OR a comparison post** — and names both engines
  per pair, because one post legitimately reporting one figure for two engines is not a defect.
- **`tests/test_duplicate_runs.py`** — the measured pair, one engine twice (not a duplicate), a
  different date or t/s (not a duplicate), a placeholder post (never evidence), the check never
  calling `fail`, its registration and stage selection, and the shipped store reporting at least one
  pair (not vacuous) while `--only data` still exits 0.

## Impact

Engine-name drift is visible in every validate run, with the pairs to look at, instead of
accumulating silently.

## Not covered (out of scope)

- `merge_engines` still appends on a rename; the ingest-side refusal (an engine name that is a quant
  or hardware token, #458) catches the fabricated case, and a genuine RENAME still duplicates — filed
  as a finding with the shape the fix needs (key on the post+date+t/s when the engine changed).
- Comparison posts remain indistinguishable from a rename by machine. The report names them; a human
  decides.
