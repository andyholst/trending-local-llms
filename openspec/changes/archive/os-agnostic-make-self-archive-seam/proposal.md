# Proposal: os-agnostic-make-self-archive-seam

Issue: #1495
PR: #1556

## Why

`#712` Slice 4 (PR #1504) routed the pure utility batch through `$(PYTHON_RUN)` but deliberately left `self-archive-snapshot` and `self-archive-guard` on the host: both read the repository's real git common directory, which a worktree keeps OUTSIDE `$PWD`, so a naive container route makes the #812 guard blind or wrong on a real checkout. A bot/keeper runner with Docker but not the pinned Python/deps still runs these two guards on the host, so the OS/toolchain leaks into the fix-loop's self-archive protection. The architect's decomposition (#712 design comment 2026-11-23T12:04:48Z) held this as the separately-owned "Slice 4b" seam change.

## What Changes

- Add the SAME `GIT_COMMON_DIR` mount that `TEST_RUN` already uses to the ONE `PYTHON_RUN` seam, so a container-routed recipe can read the worktree's real git dir (and the fix-loop baseline's host file path + `SELF_ARCHIVE_*` env, which the guard needs, are forwarded conditionally).
- Route `self-archive-snapshot` and `self-archive-guard` through `$(PYTHON_RUN)` with a `python-env-image` prerequisite; each recipe stays a PURE `python3 scripts/…` command.
- Extend `tests/test_workflows.py::test_python_env_seam_routes_migrated_recipes_through_the_container` with the Slice 4b set and the mount/forwarding assertions — RED on the pre-change tree, GREEN at this head. The existing real-repository guard tests in `tests/test_self_archive_guard.py` (unchanged) prove snapshot/check/restore behavior is preserved through the container.
- Regenerate `OPENSPEC.md`; no new script, target, pipeline job or image, so `ARCHITECTURE.md` needs no row change.

## Impact

Non-breaking: no schema, contract, API, table or data change. A Docker host now runs these two guard recipes inside the python-env container; the recipe text stays a pure `python3 scripts/…` call. The mount is the same one `TEST_RUN` has used for worktrees, and the extra env/path forwarding is conditional on `SELF_ARCHIVE_BASELINE` being set (only the fix-loop sets it), so every other `$(PYTHON_RUN)` target is byte-identical in behavior. No CI dispatch, image content change, or host-only exception list change.

## Not covered

- Slices 4's eight utility targets (already landed in PR #1504) and Slice 5's cross-cutting `scrubbed_run` / parse-time execs / host-bare-python scanner (#712).
- Any change to `PYTHON_IMAGE`, `Dockerfile.python-env`, `ensure_image.py`, or the base/test/openspec image seams.
- The pre-existing `fix_loop.sh` exit-code expectation (make returns 2 on a recipe exit 1, while the loop branches on 1) — filed separately as a finding, not changed here.
