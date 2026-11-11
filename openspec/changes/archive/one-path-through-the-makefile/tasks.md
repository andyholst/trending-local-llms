# Tasks

- [x] 1. Write the proposal + spec for the one-path rule (issue #262).
- [x] 2. `AGENTS.md` rule 6m: business logic through the Makefile, every real target called by a workflow, and no test replacing the system under test (with the external-system exception).
- [x] 3. `tests/test_makefile_only.py`: no product symbol patched/rebound/faked; a workflow reaching the product without `make`; a called target that does not exist; a CI gate target no workflow calls.
- [x] 4. Wire the guard into `make _test` (with its `main()` runner, rule 6d) and add its §8 row.
- [x] 5. Run `make lint`, `make test`, `make architecture-check`, `make openspec-check`; commit, push, open the PR (closes #262).
