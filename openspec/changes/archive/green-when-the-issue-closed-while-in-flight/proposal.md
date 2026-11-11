# Proposal: green-when-the-issue-closed-while-in-flight

Issue: #520 (measured: run 39612330011 went RED over work PR #517 had already landed)

## Why

The sweep picked `#183` at 14:37:15 while it was open. Ten seconds later PR #517 merged and closed
it. At 14:41:56 the run failed:

```
##[error]issue-bot produced no implementation for #183 (make implement-issue rc=2).
```

The agent had nothing to do because the work was **done** — and the pipeline read the identical
signature ("verdict=implement, nothing implemented") as the one it uses for a real defect (a dead
key, a burned token budget: #120/#281/#346). With `auto-merge` landing PRs continuously, that race
is routine, not exotic. #496 taught the implementer to CLOSE an already-fixed issue, but it decides
that at the START of a run, from the thread — this race happens after that decision.

## What Changes

- **`make issue-state ISSUE=<n>`** — `scripts/issue_verdict.py --state`, the one seam for "does this
  issue still need doing": exit **0 = open**, **4 = closed**, **2 = unreadable** (a state we cannot
  read is never a guess).
- **`issue-bot`'s final "Fail loudly" step asks first.** A CLOSED issue ends the run **GREEN** with a
  loud notice and ONE marker-deduplicated comment on the thread (`<!-- issue-bot-already-fixed: … -->`)
  saying the issue was closed mid-run. A still-OPEN issue keeps **both** red paths exactly as
  before, and an unreadable state stays RED — silence is not evidence.
- **Tests**: the three exit codes against a stub `gh`, and a workflow guard that the state read
  happens before the red path, that the closed branch exits 0 with the default token, that exit 2 is
  not excused, and that the open-issue paths are untouched.

## Impact

`scripts/issue_verdict.py` (`--state`), `Makefile` (`issue-state`), `.github/workflows/issue-bot.yml`,
`tests/test_issue_triage.py`, `tests/test_workflows.py`, `ARCHITECTURE.md`, `OPENSPEC.md`.

## Not covered

- **A merged PR that the sweep itself opened** landing while the run finishes (the fix loop's
  window) — a different race, its own measurement.
- **Reopening a wrongly-closed issue.** The comment tells the owner to reopen; the next sweep then
  sees it. The bot never reopens an issue itself.
