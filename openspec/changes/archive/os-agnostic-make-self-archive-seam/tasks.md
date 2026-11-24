# Tasks: os-agnostic-make-self-archive-seam

- [x] Create the OpenSpec change (`make openspec-new NAME=os-agnostic-make-self-archive-seam`) before any code edit
- [x] Add the `GIT_COMMON_DIR` mount and the conditional `SELF_ARCHIVE_*` env/baseline-path forwarding to the ONE `PYTHON_RUN` seam
- [x] Route `self-archive-snapshot` and `self-archive-guard` through `$(PYTHON_RUN)` + `python-env-image`, each recipe staying a PURE `python3 scripts/…` command
- [x] Extend `tests/test_workflows.py::test_python_env_seam_routes_migrated_recipes_through_the_container` with the Slice 4b routed targets + mount/forwarding assertions and prove them RED on `origin/master`'s Makefile (4 FAIL, every pre-existing check still ok)
- [x] Prove the seam test GREEN at the head (targeted module `python3 tests/test_workflows.py`: 1329 pass / 0 fail) and the host `make -n` expansion shows the real git-common-dir mount + baseline path + `SELF_ARCHIVE_*` env
- [x] Prove the real container round-trip on this git worktree: `self-archive-snapshot` writes the baseline back to the host path, a clean tree is green, and a controlled archive move of an active change is detected and restored (guard exit 1)
- [x] Confirm `IN_CONTAINER=1` still drops the docker harness and keeps the pure `python3 scripts/self_archive_guard.py …` command
- [x] Write `findings.md` with Evidence/Why/Done-when for the pre-existing `fix_loop.sh` exit-code expectation (`make findings-check` green)
- [x] Run the fast offline gates green at the exact head: `make lint`, `make openspec-check`, `make architecture-check` and the targeted seam-test module
- [x] Regenerate `OPENSPEC.md` with the active change bound to #1495
