# Tasks

- [x] 1. Write the proposal + capability spec for issue #190 (`syntax-lint`: a module that warns on compile is a finding, the tracked-file set, the wiring).
- [x] 2. `scripts/update_trending.py` — escape the offending `\ ` in the module docstring so the module imports without a `SyntaxWarning`.
- [x] 3. `scripts/lint_syntax.py` — the ONE implementation: the tracked `*.py` file set (`git ls-files '*.py'`), compile-from-source with `SyntaxWarning` as an error, the untracked/binary refusals, the loud finding list.
- [x] 4. `Makefile`: `make lint` runs the guard beside `lint_linefeeds.py`; `tests/test_lint_syntax.py` added to the `_test` fallback chain.
- [x] 5. `tests/test_lint_syntax.py` — the planted invalid escape, the clean tree, the untracked module, the real repository, and the wiring (CI, the fix loop, the suite).
- [x] 6. `ARCHITECTURE.md` (rule 6h): the `lint` target row and the scripts table name the guard.
- [x] 7. `AGENTS.md` §8: a guard row beside the trailing-newline row.
- [x] 8. Verified: `make lint`, `make test`, `make architecture-check`, `make openspec-check` green; the guard shown failing on the pre-change `scripts/update_trending.py`.
- [x] 9. `OPENSPEC.md` regenerated (`make openspec-index`).
- [x] 10. `findings.md` written for the gap found while working (`make openspec-status` cannot run — the target omits `--change`); `make findings-check` green.
