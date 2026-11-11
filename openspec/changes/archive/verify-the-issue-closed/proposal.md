# Proposal: verify-the-issue-closed

Issue: #288 — `tech-debt: No post-merge step verifies the referenced issue actually closed`

## Why

`make pr-closure` **PREDICTS** the closure: it reads the PR body and applies GitHub's parser
semantics (one closing keyword binds to ONE reference). It cannot prove the outcome. Measured on
PR #272: the body said `Closes #271 and #276`, the merge closed **#271**, left **#276 open**, and
every job stayed green — including `auto-merge`.

## What Changes

- **`scripts/verify_closure.py`** — after a merge, reads the merged PR's own
  `closingIssuesReferences` and fails when one is not `CLOSED`:
  - fetches an issue's state when the reference does not carry it;
  - retries briefly (`VERIFY_CLOSURE_ATTEMPTS` / `VERIFY_CLOSURE_DELAY_S`), because GitHub's
    close trails the merge call by a moment;
  - exits 1 **naming the issue, its state and the rule** the body broke;
  - is LOUD when `gh` itself fails (`[verify-closure] FAIL: gh … exited N`) — an unreadable
    state is never a pass;
  - a PR that claims to close **nothing** is not a failure (a change may reference an issue it
    does not implement; `pr-closure` refuses a *mismatch*, not an absence).
- **`make verify-closure`** (`PR=<n>` `REPO=<owner/name>`) over the host recipe
  `_verify-closure` — `gh` lives on the runner, not in the image.
- **`auto-merge` runs it as its last step**, so the merge job's verdict covers what the merge
  actually closed.
- **`tests/test_verify_closure.py`** runs the REAL script against a stub `gh` on `PATH` (an
  external system; the script's own request building and decision still execute): the closed
  case, the measured #272 shape, a reference without a state, closing nothing, a `gh` failure,
  and the wiring.
- **`ARCHITECTURE.md`** gains the target row and the `auto-merge` step (rule 6h).

Verified RED against the pre-change tree (11 failures — no script, no target, no step) and GREEN
after (`PASSED 12 | FAILED 0`).

## Impact

`scripts/verify_closure.py` (new), `Makefile` (two recipes), `qa-validate.yml` (one step),
`ARCHITECTURE.md`, a new test module, this OpenSpec change and the regenerated `OPENSPEC.md`.

## Not covered

- **Re-opening or commenting on the issue.** The job reports; a human decides what a body that
  mis-bound means (usually an edit plus a manual close).
- **A PR that closes an issue it does not implement.** `make pr-closure` refuses that shape
  before the merge; this check only proves the positive claim.
