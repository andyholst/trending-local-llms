# Proposal: verdict-hold-ceiling

Issue: #203 — `A verdict hold has no ceiling: a re-review that keeps re-dating it holds an issue for ever`

> Note: #203's own body was truncated by the extractor defect #205 fixed (it ends at
> “`scripts/issue_queue.py` computes `verdict_fresh` against”, “that is why”, “the queue
> reports how long the CURRENT verdict has been held (the”). The design below is
> reconstructed from the surviving fragments, the title and the code.

## Why

A reviewer verdict holds the implementer off an issue while it is *fresh*, and freshness
is measured from the **newest** reviewer marker:

```python
verdict_fresh = bool(verdict_label) and bool(verdict_ts) and (
    (now - verdict_ts) < dt.timedelta(hours=verdict_ttl_hours))
```

`VERDICT_TTL_HOURS` (24) exists so a verdict cannot stall the queue for ever — a label
left by a cancelled run releases the issue after a day. But a reviewer that keeps
*re-reviewing* the issue writes a fresh marker every time, and each one resets the
clock. An issue can therefore be held indefinitely by a reviewer that never decides,
and nothing in the row said how long the current verdict had been standing.

## What Changes

- **`verdict_chain_start(timestamps, ttl_hours)`** walks the reviewer markers from
  newest to oldest while consecutive markers are less than the TTL apart: the chain's
  first link is when the CURRENT verdict started being held. A gap wider than the TTL
  (a stale label from a cancelled run) breaks the chain, exactly as before.
- **`VERDICT_MAX_HOLD_HOURS` (24 × 7) is a ceiling on the whole chain.** Past it the
  hold EXPIRES: `verdict_fresh=0`, `reason=verdict-expired`, the issue is back in the
  pick order (`position=0`, `impl_skip=0`) and the run prints a loud line naming the
  held duration and the ceiling — so a reviewer that keeps re-dating a verdict cannot
  stall the queue for ever.
- **The row reports it**: `verdict_held_since`, `verdict_held_hours`, `verdict_expired`
  join `verdict`/`verdict_since`/`verdict_fresh`, so the hold's age is readable from the
  artifact the bots print.
- **`--verdict-max-hold-hours`** (env `VERDICT_MAX_HOLD_HOURS`) makes the ceiling
  injectable, like the TTL and the gap.
- **`tests/test_issue_review.py`**: a 200 h chain (markers every 20 h, newest 6 h old)
  expires and returns the issue to the pick order; a 40 h chain still holds and reports
  its age; a marker pair across a stale gap does not extend the hold.

Verified RED against the pre-change queue (7 failures — the 200 h chain stayed
`verdict-fresh` and held the issue) and GREEN after (`PASSED 76 | FAILED 0`).

## Impact

`scripts/issue_queue.py` (one helper, one constant, the freshness computation, the row
and the render line), its test module, this OpenSpec change and the regenerated
`OPENSPEC.md`. Both bots read this queue, so the implementer gets the issue back and the
reviewer sees the expiry in the log; no make target, stage, job or image changes
(`ARCHITECTURE.md` unchanged, rule 6h).

## Not covered

- **Deciding what a verdict SHOULD be.** An expired hold releases the issue to the
  implementer; it does not clear the reviewer's label (a label is a human's or the
  reviewer's, rule 6j) — the human sees the expiry line and decides.
- **The skip note for an expired hold** (#204's note is for a FRESH verdict; an expired
  one is not a hold at all).
