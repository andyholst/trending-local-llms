# Proposal: gap-reader-drops-refused-misattribution

Issue: #1007

## Why

`scripts/data_gap_analysis.py` decides "stated in prose only" (an INGEST job)
versus "never captured" (an ACQUISITION gap) by reading the free text of
`data/raw/*.json`. It never read the refusal ledger (`data/refusals.json`), so a
capture the #468 seam `refuse_misattributed_measurements` had ALREADY proven to
measure a *different* model still counted as the model's captured prose.
Measured on the live store: the post
`https://lightbrd.com/0xbelorix/status/2075607981027393583` measures
`Qwen 3.5 35B` (the seam filed a refusal for `qwen-3.6-27b` + that post on
2026-11-16), yet its sentence — "…80k context…" — sat under the refused row AND
was handed BACK by `_join_measurement_identity`'s post-identity join, so the
report flagged `qwen-3.6-27b` `context_tokens` as "stated in prose only" from a
sentence about another model, and `make data-gaps` filed its gap as the wrong
kind of work.

## What Changes

- `captured_text` gains a `refusals` parameter; `analyse` reads the ledger
  FIRST (`load_refusals()`) and passes it down, and `stated_untraceable`'s own
  default capture is ledger-aware too (rule 6d — one behavior).
- A raw source (the row or an engine row) whose `source_post` the ledger
  refused for the RESOLVED store id under stage
  `refuse_misattributed_measurements` contributes NO text.
- `_join_measurement_identity` gains the same rule: a refused
  (model, post) pair is credited through NEITHER identity path — closing the
  bypass where the join re-credits prose the scan just skipped.
- `MISATTRIBUTION_STAGE` is pinned to the seam's own registry
  (`update_trending.REFUSAL_STAGES`), and pairing uses ONE citation spelling
  (`_norm_citation`: case-, slash- and host-insensitive), never private copies
  (rule 6d).

## Impact

- `scripts/data_gap_analysis.py` — `captured_text`, `_join_measurement_identity`,
  `analyse`, `stated_untraceable`, new `_norm_citation` helper, new
  `MISATTRIBUTION_STAGE` constant. No CLI surface changes; `make data-gaps`
  output changes ONLY in classification quality.
- `tests/test_data_gap_analysis.py` — new planted guard tests (red on
  origin/master's script) and two real-store allowlists updated with measured
  values: `unstructured:context_tokens` `["qwen-3.6-27b"] -> []`,
  `untraceable:context_tokens` `["gemma-4-12b"] ->
  ["gemma-4-12b", "qwen-3.6-27b"]`.
- No data files change (rule 3b: this is reader behavior, not a store edit).

## Not covered

- The #468 seam itself (`refuse_misattributed_measurements`) is unchanged.
- Refusals at OTHER stages (e.g. `refuse_fabricated_engines`) keep their
  current meaning; only the misattribution stage removes CAPTURED TEXT here.
- No raw snapshots or ledger rows are rewritten or removed.
