# Tasks

- [x] 1. Write the proposal + spec for unique, resolvable rule numbers (issue #270).
- [x] 2. Renumber the searches rule `6m` -> `6o` and follow its citation in `tests/test_query_coverage.py` (`6m` stays the ONE-path rule).
- [x] 3. `tests/test_rule_numbers.py`: §2 ids are unique and non-empty, and every `rule <id>` citation in the tree resolves.
- [x] 4. Wire the guard into `make _test` (with its `main()` runner, rule 6d) and add its §8 row.
- [x] 5. Prove the guard fails on the pre-change rulebook (rule 6c) and passes after.
- [x] 6. Verified: `make lint` OK (592 files), `make architecture-check` OK (84 targets), `make openspec-check` green, and the suites (`test_rule_numbers`, `test_query_coverage`, `test_makefile_only`, `test_bot_markers`, `test_workflows`) pass.
