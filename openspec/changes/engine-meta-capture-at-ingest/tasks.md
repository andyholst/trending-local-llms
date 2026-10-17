# Tasks

- [x] 1. Write the proposal + capability spec for issue #334 (`engine-meta-capture`: keep the offline fixture covering every registered engine, and run the capture where an engine is registered).
- [x] 2. `scripts/engine_registry.py` — `capture_meta(store, path, fetch)`: add every missing registered engine's `full_name`/`description`/`topics`, sorted, `_source` preserved, no invented entry, idempotent.
- [x] 3. `scripts/engine_registry.py` — `--capture-meta` / `--meta-file` CLI mode beside `--check-raw`, refusing a run that names neither.
- [x] 4. `Makefile`: `_engine-meta-capture` + the public `engine-meta-capture` wrapper (rule 6d).
- [x] 5. `.github/workflows/refresh-bot.yml`: the aggregate runs `make engine-meta-capture` AFTER `make merge-fetch` and before `qa-report`.
- [x] 6. `tests/test_engine_registry.py` — the capture's behaviour (adds, refuses to invent, preserves, idempotent) and its wiring (target exists, the workflow calls it after the merge).
- [x] 7. `ARCHITECTURE.md` (rule 6h): the target row, the aggregate's step, the script's row.
- [x] 8. No-op on the current tree: `python3 scripts/engine_registry.py --capture-meta` prints `OK: the offline fixture already covers every registered engine`.
- [x] 9. Verified: `make test`, `make lint`, `make openspec-check`, `make architecture-check` green.
- [x] 10. `OPENSPEC.md` regenerated (`make openspec-index`).
- [x] 11. `findings.md`: the §8 row is owed (protected file, the #212/#310 class) — recorded for review.
