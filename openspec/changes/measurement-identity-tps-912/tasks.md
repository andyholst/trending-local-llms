# Tasks: measurement-identity-tps-912

- [x] OpenSpec change (proposal, spec with per-scenario tests, tasks)
- [x] Join widened by post identity with numeric tps comparison in `_join_measurement_identity` — verified: `tests/test_data_gap_analysis.py` PASSED 254, and the suite goes RED (2 FAIL) against `origin/master`'s old join
- [x] Loud `measurement-identity:` report line for unmatched post identities — verified by `test_an_unreconcilable_identity_is_reported_loudly`
- [x] Four new tests in `tests/test_data_gap_analysis.py` (raise keeps trace, miss reported loud, no-post needs equal tps, joint raise uncredited)
- [x] AGENTS.md §8 guard row
- [x] `make lint` green (linefeeds + syntax), `make secret-scan` clean, `OPENSPEC.md` regenerated; `make openspec-check` green
