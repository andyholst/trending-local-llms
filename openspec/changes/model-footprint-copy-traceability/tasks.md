# Tasks: model-footprint-copy-traceability (issue #934)

- [x] Capture pool + matcher in `scripts/validate.py`
      (`model_capture_footprint_index`, `_copy_figures`, `_footprint_copy_supported`,
      `model_level_footprint_flags`) — verified by `tests/test_model_footprint_copy.py` (16 green).
- [x] New data-stage check `check_model_footprint_copy` registered in `validate.py`'s stage map —
      verified green by `make _validate-data` on the shipped store.
- [x] Shipped-store reconciliation (additive, rule 3b): `qwen3-14b` `context_tokens 30k` →
      captured exact `30720`; fourteen unmarked orphan values carry `(est)` — verified by
      `test_shipped_store_has_no_untraceable_hard_copy` (residue 0).
- [x] `tests/test_model_footprint_copy.py` with the seven spec-scenario tests + live-gate proof
      (planted copy into the REAL store flags exactly once).
- [x] `AGENTS.md` §4 model-level copy sentence + §8 guard row (rule 3c — this is an attended
      run; the PR reviewer signs off on the AGENTS.md diff).
- [x] `make architecture-refresh` + `make openspec-index` regenerated in the same change.
