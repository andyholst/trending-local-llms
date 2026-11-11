# Tasks

- [x] 1. Proposal + `stage-wiring` capability spec for issue #514.
- [x] 2. `tests/test_validate.py` reads `architecture_check.stage_lists` / `validate_stages` instead of its own `--only` regex.
- [x] 3. An assertion that the two readers agree on the registered stage set.
- [x] 4. Verified the guard is wired, not merely imported: removing `removal` from every `--only` list reds it with `stage 'removal' is selected by a Makefile --only list [--only stages: [...]]`.
- [x] 5. `tests/test_validate.py` 172 passed, 0 failed.
- [x] 6. `findings.md` written; `make openspec-index`, `make openspec-check`, `make architecture-check`, `make lint` green.
