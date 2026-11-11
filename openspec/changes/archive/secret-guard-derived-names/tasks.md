# Tasks

- [x] 1. The tracked change exists (this directory) before any code edit
- [x] 2. `SECRET_FLOOR` is the floor; `secret_names(root)` adds every `${{ secrets.<NAME> }}` the workflows reference
- [x] 3. A name quoted in a workflow COMMENT declares nothing (measured: `secrets.X` in qa-validate's explanation)
- [x] 4. `_patterns(names)` builds the value-shaped rules per tree; `violations()` and `report()` use it
- [x] 5. The four import-time regexes that froze the name list are removed (no other caller)
- [x] 6. Tests: a referenced new key is guarded; a floor name needs no reference; a commented name declares nothing
- [x] 7. Verified RED on the pre-change guard (the new key produced no violation) and GREEN after (`PASSED 88 | FAILED 0`)
- [x] 8. `OPENSPEC.md` regenerated; `openspec-index-check` and `check_openspec_tasks` green
- [x] 9. `make lint`, `make test`, `make check-secret-output`, `make architecture-check` and `make openspec-check` green
