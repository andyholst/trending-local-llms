# Proposal: cross-model-alias-gate-1213

Issue: #1213
PR: #1858

## Why

Two security findings on #1213 come from one split: the write path and the read path of the
same attribution exception disagree about what justifies a cross-row duplicate. Ingest accepts
a pair pinned allow-list-exact in `CROSS_MODEL_ALLOW_LIST`, while the post-merge gate reads
only the store-side `measurement_model_aliases`. A pair migrated to the allow-list and stripped
of its alias therefore reds `validate --only data`. Separately, a counterpart whose params are
stated in a form the parser cannot read (`E4B`, `MoE`, `421M / 322M`, `MoE, ~3B active`) got a
silent alias grant at ingest and no REPORT line, so a new cross-identity attribution could
drift in while the visible ledger still read 12.

## What Changes

- `validate.cross_row_duplicate_measurements` consults `CROSS_MODEL_ALLOW_LIST` with the SAME
  identity key ingest uses, so an allow-list-exact pair is justified without an alias.
- `update_trending.cross_identity_alias_reason` fails closed when either side STATES a params
  value the parser cannot read; `merge_measurement_aliases` refuses that counterpart loudly and
  `check_measurement_alias_map` prints a REPORT line naming it. Genuinely absent params keep
  the documented #1207 fail-open, and #1210's flash-next <-> 27b hold is untouched.
- Add RED guards in `tests/test_engine_figure_alignment.py` and `tests/test_alias_identity_gate.py`.

## Impact

No data file, contract, schema, table shape, workflow or image changes. No stored key or value
is removed (rule 3b) and no model attribution is re-ruled: the two allow-list-exact pairs keep
the same evidence, and the four unparseable-params models are only refused as NEW alias targets.
The shipped store stays green; the only ledger change is that stated-unparseable counterparts
are reported instead of silent.

## Not covered

- No ruling on the twelve cross-identity alias pairs; those remain owner decisions, with #1210
  holding flash-next <-> 27b.
- No rewriting of `params` values, no new parser for `E4B`/`MoE`, and no data capture.
- No merge, master push, collaborator grant, cron or GitHub Actions schedule.
