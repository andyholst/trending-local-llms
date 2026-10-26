# Tasks

- [x] 1. Proposal + `data-integrity` capability spec for issue #459.
- [x] 2. `duplicate_runs(models)`: grouped on (source_post, date, t/s), multi-engine groups only, placeholder posts excluded.
- [x] 3. `check_duplicate_runs`: report only, registered in the `data` stage so `make validate` and every refresh print it; the wording distinguishes a renamed engine from a comparison post.
- [x] 4. `tests/test_duplicate_runs.py` (12 checks): the measured pair, same engine twice, a different date/t-s, a placeholder post, never-fails, registration + stage selection, and the shipped store.
- [x] 5. `make validate --only data` measured on the shipped store: 22 figures reported, exit 0.
- [x] 6. `findings.md` written; `make openspec-index`, `make openspec-check`, `make architecture-check`, `make lint` green.
