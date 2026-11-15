# Tasks

- [x] 1. The tracked change exists (this directory) before any code or test edit
- [x] 2. `scripts/run_tests.sh` exports `PYTHONDONTWRITEBYTECODE=1` (the ONE seam,
      covering container `_test:`, host, and direct invocation)
- [x] 3. `tests/test_no_bytecode_litter.py` (new module, auto-discovered by the
      runner) proves: the control litter is real (guard fails on the pre-fix
      runner), the real runner is green with the `[test] ok` trace intact and
      leaves zero `__pycache__`, the seam owns the flag, and `make test` still
      reaches the suite only through the runner (rule 6m)
- [x] 4. Gates green on the exact head: `make lint`, the full `make test`
- [x] 5. `make openspec-index` regenerated; AGENTS.md §8 guard row added
