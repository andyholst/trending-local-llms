# Tasks

- [x] 1. `ARCHITECTURE.md` exists and describes the data flow, every public make target, every pipeline job, the three images, every script and the life of a change
- [x] 2. `scripts/architecture_check.py` fails on a missing/undocumented target, a stale target claim, an undescribed workflow or script, and a phantom reference
- [x] 3. `make architecture-check` is wired into `qa-validate`'s `validate` job, the fix loop and `make test`
- [x] 4. `AGENTS.md` rule 6h states the obligation and its §8 row names the guard
- [x] 5. The implementer prompt requires the `ARCHITECTURE.md` update and `make architecture-check`
- [x] 6. `README.md` (through its template) points at the file
- [x] 7. `tests/test_architecture.py` locks every failure mode and the wiring, and fails on the pre-change tree
- [x] 8. This change is tracked (proposal + capability spec with Given/When/Then + `- **Test:**` lines), listed in `OPENSPEC.md`, and every box here is ticked
- [x] 9. `make architecture-check`, `make openspec-check`, `make test`, `make validate`, `make validate-mapped` and `make secret-scan` are green
