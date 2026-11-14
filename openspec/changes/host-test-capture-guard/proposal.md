# Proposal: host-test-capture-guard

Issue: #911

## Why

`make test` on the host is the wrapper every developer and every bot uses, yet
it can answer rc 0 over a capture that contains NOTHING from the suite
(measured 2026-11-14 on a worktree branch: the captured log held only the
recipe echo and the platform warning, `SUITE_RC=0`). Two defects compose:
`scripts/run_tests.sh` `mktemp`'d a passing module's output and deleted it, so
a fully green suite was ONE verdict line and a lost container stream was
indistinguishable from a clean run; and `TEST_RUN` lacked the explicit
`-e PYTHONUNBUFFERED=1` the DOCKER_RUN lesson (issue #591, "block-buffers its
output and writes nothing until it exits") already teaches. A green rc that
cannot show the work behind it is not a green.

## What Changes

- `scripts/run_tests.sh` prints `[test] ok <module>` for every PASSING module
  (module chatter stays out of the stream; the stop-at-first-red contract with
  the failing module's full output is unchanged).
- `TEST_RUN` forwards `-e PYTHONUNBUFFERED=1` explicitly, like `DOCKER_RUN`.
- The public `test:` target tees the container stream into a capture and
  refuses — loudly, `[harness] FAIL … UNVERIFIABLE`, exit 1 — when no
  `[test]` line arrived; when lines did arrive it reports the per-module trace
  count and the suite's rc, and propagates that rc.
- New suite `tests/test_test_capture_guard.py` locks all three end to end
  (the real runner and the real recipe run; only the container is a PATH stub,
  rule 6m).

## Impact

- `Makefile` (`TEST_RUN`, `test:`), `scripts/run_tests.sh`, `tests/`
- AGENTS.md §8 guard row
- CI is unchanged in semantics: `make test` stays the entry point; a suite that
  prints its verdict (it always has) passes exactly as before — only an empty
  capture newly fails.

## Not covered

- The platform warning (`WARNING: The requested image's platform…`) stays as
  is; issue #919 owns the arm64 image question.
- No change to `_test` (the in-container recipe) or to any module's output.
