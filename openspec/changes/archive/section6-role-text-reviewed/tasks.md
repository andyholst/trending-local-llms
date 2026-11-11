# Tasks

- [x] 1. Write the proposal + `architecture-role-boundary` capability spec for issue #508.
- [x] 2. `ARCHITECTURE.md` §6 lead-in: state plainly that the Role column is review text (first-cell presence only), with the matching line in the top boundary.
- [x] 3. `scripts/architecture_check.py`: `described_scripts()` docstring states the same first-cell boundary.
- [x] 4. `tests/test_architecture.py`: `test_section6_role_text_is_reviewed_not_verified` locks both statements (document + docstring).
- [x] 5. `findings.md` written; `python3 tests/test_architecture.py` (51/51) and `python3 scripts/architecture_check.py` green; docker-wrapped `make test`/`make openspec-check` not runnable in this container (no docker) — verified via the stdlib seams they wrap.
- [x] 6. `OPENSPEC.md` regenerated (`python3 scripts/openspec_index.py --write`) so the change has a row.
