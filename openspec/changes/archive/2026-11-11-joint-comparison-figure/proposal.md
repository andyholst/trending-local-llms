# Joint comparison figure (issue #651)

## Why
`misattributed_measurement_reason` returns None as soon as the text carries a
comparison cue, so a measurement whose `quant` reads "Qwen 3.6 27B vs Qwen 3.5
35B: 140 t/s" is kept on the 27B row even though the single figure may be the
35B model's. A comparison row can silently carry the other model's number.

## What Changes
- The comparison cue no longer rescues EVERY sentence: when the text names a
  same-family, different-params model AND carries EXACTLY ONE t/s figure, the
  figure is JOINT — it cannot be attributed to one row — and ingest REFUSES the
  measurement loudly (same seam as `refuse_fabricated_engines`, issue #458).
- "One figure per model" bake-offs (two or more t/s figures), cue-bearing
  context with no figure, own-phrase multi-model posts and documented
  `MEASUREMENT_MODEL_ALIASES` exceptions keep their existing behaviour.
- The validator's attribution scan stays REPORT ONLY (rule 3b: history is
  never removed); the refusal applies to incoming measurements only.

## Impact
- `scripts/update_trending.py` — `misattributed_measurement_reason` (one
  implementation; ingest refusal and the validator report both call it, rule 6d).
- `tests/test_measurement_attribution.py` — joint-figure refusal + bake-off
  keep tests.

## Not covered
- Splitting a joint figure into two rows (would invent attribution the post
  does not state). Cross-family comparison text is out of scope (unchanged).
