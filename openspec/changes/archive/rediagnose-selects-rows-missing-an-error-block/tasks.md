# Tasks: rediagnose-selects-rows-missing-an-error-block

- [x] `scripts/pipeline_failure_issue.py`: add the ONE diagnosis predicate `row_is_diagnosed(entry)`
  (a row is diagnosed when it stores `error_excerpt`, or the legacy `rediagnosed_excerpt`) and route
  the re-diagnosis pass, the attribution report and the attribution refusal through it (issue #1136)
- [x] Replace the marker-key pending filter with the ONE seam `rediagnose_pending(ledger)` — NOT
  diagnosed AND no `rediagnosed_utc` AND not the terminal `log_expired` drain — so a stamped row with
  no error block is selected; keep `undiagnosed` in the row (rule 3b, nothing removed)
- [x] Make a filing record its own diagnosis in the ledger row (`error_excerpt`, scrubbed through
  `scripts/scrub_log.py` before the write — `data/pipeline_failures.json` is a tracked file, rule 3d),
  and name NO block when the log read failed, so a diagnosed filing is never re-fetched or
  self-annotated in the same sweep
- [x] `scripts/pipeline_failure_guard_check.py`: classify a stamped row by diagnosis — an attributed
  row with no error block becomes its OWN reported line (naming the fix PR, the guard and
  `rediagnose_pending`), never the closed-without-guard refusal and never red; `summary()` reports
  `diagnosed_attributed` and `attributed_without_diagnosis` separately; a stamped row whose guard was
  deleted stays RED
- [x] `tests/test_pipeline_failure_issue.py`: plant the measured stamped-and-errorless row beside an
  already-diagnosed row, prove the old marker-key filter selected nothing and the new seam selects
  exactly that row, prove the sweep fetches and raises it append-only, prove diagnosed rows are
  byte-identical and a re-sweep writes nothing, and assert the COMMITTED ledger's pending set is
  exactly the five measured runs (issues #1039–#1043) — `test_a_stamped_row_with_no_error_block_is_pending_and_gets_diagnosed`,
  `test_the_committed_ledger_s_errorless_rows_are_exactly_the_pending_set`
- [x] Extend `test_filing_diagnoses_every_failure_with_the_log_error_block` (the filed row carries a
  scrubbed `error_excerpt`; no re-fetch, no self-annotation) and `test_undiagnosed_filing_is_loud_never_a_skip`
  (no block, stays pending)
- [x] `tests/test_pipeline_failure_guard.py`: `test_a_stamped_row_with_no_error_block_is_its_own_report_never_red`
  and `test_the_committed_ledger_classifies_its_five_errorless_rows` (the REAL gate over the
  committed ledger names all five run ids and reports the two classes separately); keep
  `test_a_stamped_row_whose_named_guard_no_longer_exists_is_red` green
- [x] `tests/test_pipeline_failure_attribution.py`: `test_a_stamped_row_with_no_error_block_refuses_an_attribution_claim`
  (exit 2, ledger and issue comments untouched)
- [x] `AGENTS.md` §6r states the selection rule (absence of a diagnosis, never the presence of an
  `undiagnosed` key) and adds the two §8 guard rows this change owed (rule 6c/3c — attended change,
  the AGENTS.md diff is review-required at the PR)
- [x] `ARCHITECTURE.md`: the `make pipeline-failure-issue` target row, the
  `make pipeline-failure-guard-check` target row and the two `scripts/` rows (§6) describe
  `rediagnose_pending`, `row_is_diagnosed` and the two guard classes; `make architecture-check` green
- [x] Gates green on this branch: `make test`, `make lint`, `make openspec-check`,
  `make architecture-check`, `make secret-scan`, `make pipeline-failure-guard-check`
- [~] Post the diagnosis outcome on issue #1136 after the next `queued-alarm` sweep re-reads the five rows — blocked: owner-dispatched sweep only (rule 6t: agents never dispatch a pipeline); the product-side half is DONE here — `make pipeline-failure-guard-check` on the committed tree names all five rows and `rediagnose_pending` selects exactly them
