# The reviewer's pick output is parsed as a number, and a failed step stops its dependants

**Issue:** [#344](https://github.com/andyholst/trending-local-llms/issues/344)
**Capability:** `issue-review-queue`

## Why

`make review-issue-pick` prints ONE diagnostic line per candidate before the
`action=`/`issue=`/`path=`/`reason=` block, and each diagnostic line begins with
`issue=…` (`scripts/issue_review.py:114`). The reviewer workflow parses the key with

```
value=$(printf '%s\n' "$OUT" | sed -n "s/^${key}=//p" | head -1)
```

so `ISSUE` never becomes a number: it becomes the first candidate's whole tail,
e.g. `266 position=-1 window=open reason=decided:agent:refined started=0
reply_recent=0 review_recent=0` (measured in run 39040689085). Two failures follow:
`gh issue view "$ISSUE"` cannot resolve the issue, and the `always()` window-close
step runs `make review-issue-finish ISSUE="$ISSUE"` → `issue_review.py: error:
unrecognized arguments: …`. The reviewer therefore never reviews, and a run leaves
`review-in-progress` and its start marker behind — a dead window the implementer's
sweep then defers to (the `VERDICT_TTL_HOURS` failure arriving by another route).

The second half is the workflow's dependency shape: the failed thread step does not
stop the steps that consume `ISSUE`, so one broken value produces two failures and
no readable summary.

## What Changes

- **`scripts/issue_review.py`** — `--pick`'s per-candidate diagnostics are printed on
  a `candidate=` line (`candidate=266 position=…`), so the ONLY line that starts with
  `issue=` is the action's, and it carries the NUMBER alone.
- **`.github/workflows/issue-review-bot.yml`** — the pick step reads the FIRST token
  of each key and REFUSES an `issue=` value that is not numeric; the resolve step
  refuses a non-numeric `ISSUE` before any `gh` read; the thread step carries
  `id: thread` and every step that consumes its value is gated on
  `steps.thread.outcome == 'success'`; the `always()` window close is gated on
  `steps.mark.outcome == 'success'`, so it closes only a window this run opened.
- **`Makefile`** — one internal `_review-issue-number` guard, a prerequisite of every
  `review-issue-*` target that takes `ISSUE=`, refuses a value that is not digits
  with a message naming the parse defect instead of dying inside argparse.
- **`tests/test_issue_review.py`** — the row assertions move to `candidate=`, plus a
  test that runs the REAL `--pick` output through the workflow's OWN shipped `run:`
  block (a stub `make` stands in for the external command) and asserts `ISSUE` is the
  number, and that the OLD output shape is refused rather than silently accepted.
- **`tests/test_workflows.py`** — the wiring guards: the thread step has an id, its
  consumers are gated on it, the close is gated on the mark, and the pick validates
  numericity.
- **`AGENTS.md`** — the §8 guard row.
- **`ARCHITECTURE.md`** — the new internal target and the reviewer's steps.

## Impact

Only the reviewer's dispatch path: no data change, no README change, no ranking
change. The output of `--pick` keeps every diagnostic value, on a line no key parser
claims.

## Not covered (out of scope)

- `scripts/issue_queue.py`'s own row format (`issue=<n> position=…`) is unchanged:
  `issue-bot` already parses it with a positional rule that extracts the number
  (`sed -n 's/^issue=\([0-9][0-9]*\) position=0 .*/\1/p'`), and it is the queue's
  documented line shape, not a key parser.
- No live run is dispatched from this change (the pipeline dispatches on merge); the
  regression is locked by the shipped-step test.
