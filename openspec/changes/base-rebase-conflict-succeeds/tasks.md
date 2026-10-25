# Tasks

- [x] 1. Write the proposal + `worktree-base` capability spec for issue #586.
- [x] 2. `make base-rebase` normalises exit 3 into success with `base_rebase=conflict`, and is written `rc=0; cmd || rc=$?` so it behaves the same under `bash -e`.
- [x] 3. The issue-bot commit step calls the target without comparing an exit code make rewrites.
- [x] 4. `tests/test_base_rebase_exit_code.py` runs the REAL recipe text against a stub script (3 → success + marker, 1/2/4 → failure, 0 → clean).
- [x] 5. Verified RED on `origin/master`'s Makefile + workflow (4 failures) and GREEN after (14 passed).
- [x] 6. `findings.md` written; `make openspec-check`, `make architecture-check`, `make lint` green.
