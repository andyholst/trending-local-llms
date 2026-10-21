# Tasks

- [x] 1. `scripts/lint_linefeeds.py` fails closed on a tracked text file without a final newline and names it
- [x] 2. `--fix` appends exactly one newline, is idempotent, and skips binary/empty files and untracked files
- [x] 3. `make lint` / `make lint-fix` exist and are named in `ARCHITECTURE.md` (rule 6h)
- [x] 4. `qa-validate` runs `make lint` as its first step; `scripts/fix_loop.sh` runs it as its first check; `tests/test_lint_linefeeds.py` runs in `make test`
- [x] 5. `.editorconfig` carries `insert_final_newline = true` (LF)
- [x] 6. The 5 offending files are repaired by `make lint-fix` and the gate is green
- [x] 7. `AGENTS.md` rule 6i + §8 row; `README.md` (through its template) documents the gate
- [x] 8. `tests/test_lint_linefeeds.py` locks every failure mode and the wiring, and fails on the pre-change tree
- [x] 9. Tracked change (proposal + capability spec with Given/When/Then + `- **Test:**` lines), listed in `OPENSPEC.md`, every box ticked
- [x] 10. `make lint`, `make architecture-check`, `make openspec-check`, `make test`, `make validate`, `make validate-mapped` and `make secret-scan` are green
