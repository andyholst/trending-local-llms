# Tasks

- [x] 1. The tracked change exists (this directory) before the code edit
- [x] 2. `scripts/check_pytest_imports.py` — import/member refusal, comment-line tolerance, exit 0/1/2
- [x] 3. `make check-pytest-imports` public target bundled into the `lint` recipe (rule 6d)
- [x] 4. `tests/test_pytest_import_guard.py` — planted fixtures red, clean tree and comment green, real `tests/` green, lint wiring
- [x] 5. `ARCHITECTURE.md` §6 rows (lint target table + scripts table) and `AGENTS.md` §8 guard row
- [x] 6. `make architecture-refresh` + `make architecture-check` green
- [x] 7. `make lint`, `make openspec-check` green; `OPENSPEC.md` regenerated
- [x] 8. `make test` proven through CI (the TEST image is CI's half; local host gates green)
- [x] 9. `findings.md` written
