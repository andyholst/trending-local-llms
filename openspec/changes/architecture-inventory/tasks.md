# Tasks

- [x] 1. The tracked change exists (this directory) before any code edit
- [x] 2. `scripts/architecture_bot.py`: the block is derived from the tree (workflows → triggers/crons/jobs/`needs`/`make` calls with the Makefile's descriptions; FLOW; one line per script; README sections)
- [x] 3. `run:` bodies only — a `make` in a workflow comment, or one naming no real target, is not reported; a matrix call renders as `search-*`
- [x] 4. `--write` regenerates between the markers; `--check` fails on a stale block and on a FLOW reference the tree no longer backs (and `--write` refuses to publish an unbacked flow)
- [x] 5. `make architecture-refresh` writes; `make architecture-check` also runs `--check` (so `qa-validate`, the fix loop and `make test` gate the block)
- [x] 6. `.github/workflows/architecture-bot.yml`: daily `13 5`, owner guard first, `base-check`, refresh, check, PR only on drift, no merge, no `master`, no closing keyword
- [x] 7. `ARCHITECTURE.md`: §10 (markers + explanation), §3 `architecture-refresh` row, §4 the new pipeline and the real workflow count; block generated and `--check` green
- [x] 8. `AGENTS.md`: rule 6h extended, §6b pipeline bullet, §8 guard row
- [x] 9. `tests/test_architecture_bot.py` (fixture trees + the real repo) and the `BOT_GUARDS` registration in `tests/test_workflows.py`
- [x] 10. `OPENSPEC.md` regenerated; `make openspec-check`, `make lint`, `make architecture-check`, `make validate`/`validate-mapped`, `make test` and `make findings-check` run
- [x] 11. `findings.md` written; findings filed as their own issues (never fixed here)
