# Tasks

- [x] 1. The tracked change exists (this directory) before any code edit,
      with a capability spec and this checklist
- [x] 2. `scripts/update_trending.py`: `weight_gb_contradiction_reason` + `refuse_weight_gb_contradictions`
      — a stated `weight_gb` more than `WEIGHTS_CONTRADICTION_FACTOR` away from the model's own
      footprint is refused, with the source post; fail-open carve-outs
- [x] 3. `refuse_weight_gb_contradictions(m, store)` is wired into `ingest_raw_snapshots` at the
      same seam as the #458/#468/#702 refusals, loudly naming the model, the measurement and the post
- [x] 4. `scripts/validate.py`: `check_weight_gb_contradictions` — a report-only scan in the
      `data` stage that prints any store row whose measurement footprint contradicts its model's own
- [x] 5. `tests/test_weight_gb_contradiction.py` (new): locks the refusal over the exact shipped
      Bonsai 2 9B row, the fail-open carve-outs, the ingest wiring and the report-only scan
- [x] 6. `data` corrected additively: the `~493GB NVFP4` measurement is removed from
      `bonsai-2-9b`; `README.md` and the newest snapshot regenerated; no other value changes
- [x] 7. Gates green (run as their python equivalents in this agent container — docker is absent):
      `scripts/run_tests.sh`, `scripts/validate.py --only data,schema,mapping,removal,readme`,
      `scripts/openspec_index.py --check`, `scripts/check_openspec_tasks.py`; `.gitignore`
      unchanged; newline terminators hold
