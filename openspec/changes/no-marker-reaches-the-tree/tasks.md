# Tasks

- [x] 1. Write the proposal + `bot-commit-safety` capability spec for issue #588.
- [x] 2. `scripts/check_conflict_markers.py`: `git ls-files`, all four marker shapes, binary skip, ignored/untracked never scanned, paths + lines named.
- [x] 3. `make check-conflict-markers` (+ `_` host recipe) and `make lint` runs it.
- [x] 4. Both bot commit steps run it immediately BEFORE `git add -A`.
- [x] 5. `tests/test_conflict_marker_guard.py` against real repositories, and the workflow wiring asserted on the real text.
- [x] 6. Verified RED on `origin/master`'s tree (16/16 checks fail, script absent) and GREEN after (16/16).
- [x] 7. Stub `make`s in `tests/test_workflows.py` learn the target (the step tests run the real steps).
- [x] 8. `findings.md` written; `make openspec-check`, `make architecture-check`, `make lint`, `make test` (`test_workflows` 864) green.
