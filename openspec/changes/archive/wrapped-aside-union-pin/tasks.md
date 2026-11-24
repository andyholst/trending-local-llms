# Tasks: wrapped-aside-union-pin

- [x] Add the RED-first wrapped-aside regression test in `tests/test_fleet_lifecycle.py` and observe it fail on the current per-line normaliser
- [x] Replace `_PARENTHETICAL` with `_mask_parentheticals`, a wrapping-aware mask of every balanced parenthetical group
- [x] Route `mirror_units`, `_clauses_of` and `_is_duplicate_new_unit` through the one masked text
- [x] Prove the teeth stay RED: a clause repeated outside any aside, an exact repeated bullet, the same-line aside and an unmatched opener
- [x] Regenerate `OPENSPEC.md` and run the targeted module plus `make lint`
