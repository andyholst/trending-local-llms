# Tasks

- [x] 1. The tracked change exists (this directory) before any code edit
- [x] 2. Measured the gap: 9 of 46 scripts absent from §6 (`architecture_bot`, `code_review`, `env_int`, `install_hermes_ci.sh`, `pr_health`, `queued_run_alarm`, `refresh_base`, `sweep_alarm`, `verify_closure`)
- [x] 3. `architecture_check.py`: `section()` + `described_scripts()` (first cell only) and a finding when a script has no §6 row
- [x] 4. Proven to bite on the pre-change document: the check named exactly those 9 files
- [x] 5. The 9 rows written from the code (modes, exits, wiring, the issue each behaviour came from)
- [x] 6. `make architecture-check` and `make architecture-bot --check` green on the real tree
- [x] 7. `tests/test_architecture.py`: the fixture writes a §6 table; the new case fails without a row and passes with one (23 checks)
- [x] 8. `AGENTS.md`: rule 6h and the §8 row name the §6 requirement
- [x] 9. `OPENSPEC.md` regenerated; `make openspec-check`, `make lint`, `make architecture-check`, `make test`, `make validate-mapped` run
- [x] 10. `findings.md` written
