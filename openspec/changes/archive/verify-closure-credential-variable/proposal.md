# Proposal: verify-closure-credential-variable

Issue: #1695
PR: #1697

## Why

`scripts/verify_closure.py::_gh` refused a failing `gh` with the command, its exit code and
the raw stderr — never WHICH credential the process was using. Run 45512193546 produced
`[verify-closure] FAIL: gh issue view 1668 --json state … exited 1: HTTP 401: Bad credentials`,
so diagnosing #1677 meant hand-diffing two runs' step environments: a bare 401 is
indistinguishable from an expired token, a rotated secret and a missing scope (rule 6d — a red
gate that explains itself).

## What Changes

- Add `credential_variable()` to `scripts/verify_closure.py`: `GH_TOKEN` when it is set, else the
  default `GITHUB_TOKEN`.
- Name that VARIABLE in `_gh`'s refusal, beside the command, the exit code and gh's own stderr.
  No value is ever printed (rule 3d).
- Extend `tests/test_verify_closure.py` to drive the REAL `_gh` against a stub `gh` that exits 1
  under both spellings, assert that no value reaches the log, and run `origin/master`'s own
  script through the same stub (RED before the merge, GREEN after).
- Declare the owed §8 row for the module in `findings/1695.md` (rule 3c — `AGENTS.md` is a
  protected agent-instruction file in a headless leg). `ARCHITECTURE.md`'s two `verify-closure`
  rows are updated in the same change.

## Impact

No data format, contract, image, workflow or pipeline-wiring change. The refusal gains one
clause; every existing assertion on it (`exited N`, the issue number, its state) still holds,
and `make check-secret-output` still sees a NAME where it would have seen a value.

## Not covered

- No new credential, scope or secret, and no change to which token any job forwards.
- No `AGENTS.md` edit — the §8 row is declared as an owed row instead.
