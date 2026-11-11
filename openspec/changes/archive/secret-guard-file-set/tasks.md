# Tasks

- [x] 1. The tracked change exists (this directory) before any code edit
- [x] 2. `tracked_files()` returns every text file (binary and empty skipped), not a suffix whitelist
- [x] 3. `executes_commands(path)` gates the command-shaped rules; the shape rule applies everywhere
- [x] 4. The widened guard runs clean over the real tree (898 files scanned, 0 violations)
- [x] 5. Tests: a `.txt`/`.toml` value is caught; prose quoting the shape is not; a pasted value still is; binary/empty skipped
- [x] 6. Verified RED on the pre-change guard (3 failures) and GREEN after (`PASSED 91 | FAILED 0`)
- [x] 7. `OPENSPEC.md` regenerated; `openspec-index-check` and `check_openspec_tasks` green
- [x] 8. `make lint`, `make test`, `make check-secret-output`, `make architecture-check` and `make openspec-check` green
