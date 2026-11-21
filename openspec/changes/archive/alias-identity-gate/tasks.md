# Tasks: alias-identity-gate (issue #1207)

- [x] T1: `params_identity` + `cross_identity_alias_reason` (ONE implementation) in scripts/update_trending.py.
- [x] T2: ingest `merge_measurement_aliases(..., store)` refuses a new cross-identity counterpart; back-compat union without store.
- [x] T3: `misattributed_measurement_reason` treats a non-pending cross-identity alias as inert; `CROSS_IDENTITY_ALIAS_PENDING_RULING` holds the #1210 pair.
- [x] T4: validate `check_measurement_alias_map` REPORTS shipped cross-identity pairs (#650 precedent); dangling hard-fail unchanged.
- [x] T5: data cleanup (3 non-load-bearing contaminants) + official params note; README re-rendered.
- [x] T6: tests/test_alias_identity_gate.py 23/23; regressions cross-model 98/0, measurement-attribution 60/0, engine-figure-alignment 32/0; `validate --only data` QA PASSED.
- [x] T7: PR opened, `make pr-message-check`, `make openspec-record-pr ISSUE=1207 PR=#1215` at the PR head.