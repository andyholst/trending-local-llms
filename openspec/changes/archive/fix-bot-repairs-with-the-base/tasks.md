# Tasks

- [x] 1. The tracked change exists (this directory) before any edit
- [x] 2. `scripts/fix_loop.sh`: every Hermes round runs under `timeout "$HERMES_FIX_TIMEOUT"`; a timed-out round is named in the log and in the report
- [x] 3. `Makefile`: `HERMES_FIX_TIMEOUT := 1800` beside `HERMES_FIX_REASONING`; `_fix` bounds the `hermes` call; the `fix` wrapper forwards the same variable into the container (one number, both sides)
- [x] 4. `merge_base()` fetches `origin/$FIX_BASE` (unshallowing first) and merges it BEFORE the first LLM round; a failure the base already fixed costs zero LLM rounds; no checkout / no fetch / a conflict is a loud no-op
- [x] 5. A round that leaves the failure byte-identical AND the tree unchanged stops the loop with the reason recorded (asked only inside a git checkout)
- [x] 6. Loop-written notes survive `run_checks`' per-round truncation (`$QA_REPORT.notes`, folded in by the next `run_checks`)
- [x] 7. `tests/test_fix_loop.py` gains four guards (bound, base merge, no checkout, no progress) and runs the loop hermetically (`cwd` outside this checkout, base merge off unless a test asks for it)
- [x] 8. Every new guard was proved RED against the pre-change `scripts/fix_loop.sh` (5 FAIL) and GREEN after
- [x] 9. `tests/test_hermes_prompts.py`: the dry-run guard accepts a bounded `hermes` call and requires `_fix` to be bounded — proved RED against the pre-change `Makefile`
- [x] 10. `findings.md` records the `AGENTS.md` §8 rows this run cannot write and the buffered-stdout finding
- [x] 11. `OPENSPEC.md` regenerated; `make openspec-check`, `make architecture-check`, `make lint`, `make validate`, `make test` green
