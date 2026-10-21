# Tasks

- [x] 1. The loop is measured and recorded on #472 (12 issues, one dimension, counts 31 → 59)
- [x] 2. The tracked change exists (this directory) before any code edit
- [x] 3. `analyse()` builds a per-DIMENSION signature (`contract:` / `missing:` / `unstructured:`)
- [x] 4. The per-model detail stays in the report and the issue body
- [x] 5. A model joining an existing gap no longer changes the signature (the fix)
- [x] 6. A real change still exits 1 under `--check`; `already_filed()` untouched
- [x] 7. Tests updated to the new semantics (rule 6b): 4 assertions, 3 new checks
- [x] 8. `make test`, `make lint`, `make architecture-check`, `make openspec-check` green; `OPENSPEC.md` regenerated
- [x] 9. `findings.md` written (rule 6g)
