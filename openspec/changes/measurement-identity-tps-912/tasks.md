# Tasks: measurement-identity-tps-912

- [x] OpenSpec change (proposal, spec with per-scenario tests, tasks)
- [ ] Join widened by post identity with numeric tps comparison in `_join_measurement_identity` — verified when the new tests pass
- [ ] Loud `measurement-identity:` report line for unmatched post identities — verified by `test_an_unreconcilable_identity_is_reported_loudly`
- [ ] Four new tests in `tests/test_data_gap_analysis.py` (raise keeps trace, miss reported loud, no-post needs equal tps, joint raise uncredited)
- [ ] Full local gates: `make lint`, `make secret-scan`, `make openspec-check`, `tests/test_data_gap_analysis.py`, `make openspec-index`
- [ ] PR opened with the five-section body and `closes #912` (never draft)
