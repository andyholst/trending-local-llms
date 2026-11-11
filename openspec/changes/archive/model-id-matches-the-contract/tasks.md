# Tasks

- [x] 1. The failure is measured on PR #461 (three schema errors from one `_`)
- [x] 2. The tracked change exists (this directory) before any code edit
- [x] 3. `ID_PATTERN` + `contract_id()` — the contract's rule in one place
- [x] 4. `write_raw_snapshot` normalises the id it writes
- [x] 5. `normalize_model` normalises a provided id at ingest (never renames a stored one)
- [x] 6. Tests: the measured id, mixed case, legal-untouched, nothing-legal fallback, raw + ingest
- [x] 7. `make test`, `make lint`, `make architecture-check`, `make openspec-check` green; `OPENSPEC.md` regenerated
- [x] 8. `findings.md` written (rule 6g)
