# Tasks

- [x] 1. Write the proposal + spec for the derived guard registry (issue #313).
- [x] 2. `tests/test_workflows.py`: derive the guarded pipelines from the tree (`_guard_step_index`, `discovered_guards`, `_dispatchable`).
- [x] 3. `test_the_guard_registry_is_derived_from_the_tree`: both directions + the job agreement + the dispatchable-must-be-guarded direction + a non-vacuity floor.
- [x] 4. Register the test in `main()`.
- [x] 5. Verify RED under falsification (an unregistered guard, a vanished guard, a dispatchable pipeline with no guard) and green as it stands.
- [x] 6. `AGENTS.md` §8 row + §6j wording: written out as `AGENTS-ROW.md` and filed as [#405](https://github.com/andyholst/trending-local-llms/issues/405) for a human to apply — `AGENTS.md` is a protected file (rule 3c) and the write is approval-gated, so this run may not make it.
- [x] 7. `make test`, `make openspec-check`, `make architecture-check`, `make lint`, `make secret-scan` green.
- [x] 8. Commit, push, open the PR (`closes #313`; #405 stays open for the rulebook edit).
