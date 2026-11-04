# Tasks

- [x] 1. Write the proposal + capability spec (refresh PR carries the engine-metadata fixture it captured).
- [x] 2. `.github/workflows/refresh-bot.yml`: `tests/fixtures/github_meta.json` in the commit step's `git diff --quiet` change check.
- [x] 3. `.github/workflows/refresh-bot.yml`: `tests/fixtures/github_meta.json` in the commit step's `git add` list.
- [x] 4. `tests/test_engine_registry.py`: the capture-meta test asserts the commit step names the fixture path in both lists.
- [x] 5. Verified: `python3 tests/test_engine_registry.py`, `make lint`, `make openspec-check` (seams), `make validate-mapped`.
- [x] 6. `OPENSPEC.md` regenerated / index current.
- [x] 7. `findings.md` written (rule 6g).
