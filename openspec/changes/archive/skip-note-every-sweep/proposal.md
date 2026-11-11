# The skip note is posted on every sweep, not only on a sweep that found nothing

**Issue:** [#202](https://github.com/andyholst/trending-local-llms/issues/202)
**Capability:** `issue-review-queue`

## Why

`make issue-skip-note` says, on the issue itself, why the implementer did not take it —
one comment per review round, carrying the reviewer's own timestamp
(`<!-- issue-bot-skip: <ISO8601Z> verdict=<label> since=<reviewer ts> -->`). It exists to
answer "why is nobody working on this?" where the issue lives.

The workflow defeated it. `.github/workflows/issue-bot.yml` gated the step:

```yaml
- name: Note a fresh reviewer verdict on the issue it holds
  id: verdict
  if: steps.pick.outputs.issue == ''
```

So the note ran **only** when the pick found nothing at all. A sweep that took one issue —
the normal case, one issue per hour — skipped every OTHER held issue and said nothing about
any of them. The script half is already right (`scripts/issue_queue.py::post_skip_note`
walks every hold, bounded by `MAX_SKIP_NOTES`, idempotent per `since=`); the gate made it
unreachable exactly when it mattered.

The test suite pinned the defect: `tests/test_workflows.py` asserted
`steps.pick.outputs.issue == ''` on that step, so the wiring could not be fixed without
flipping the assertion with it.

## What Changes

- **`.github/workflows/issue-bot.yml`** — the `if:` gate is removed, so the step runs on
  every working sweep. Idempotence is unchanged: a second sweep in the same review round
  finds its own `since=` marker and posts nothing.
- **`tests/test_workflows.py`** — the assertion flips: the step must NOT be gated on the
  pick's output, so the gate cannot come back.
- **`ARCHITECTURE.md`** — the `pick` → verdict note row says "on every sweep", naming
  issue #202.
- **`AGENTS.md`** §8 — the existing guard row names the measured gate, so the defect and
  its guard stay legible together (review-required, rule 3c).

## Impact

The pick job's step list only. No data, no README, no ranking. A sweep now costs one extra
comment per held issue per review round, and nothing when the round is unchanged.

## Not covered (out of scope)

- `make issue-skip-note` re-reads the whole queue (`scripts/issue_queue.py::build`) although
  the `pick` step just computed it, so a sweep makes the API reads twice. Removing that
  duplication means one target computing the pick AND the notes in one process — a larger
  change, filed as a finding.
- The `issues: opened` path never runs the `pick` job at all, so no note is posted there.
  That path also reads no queue, so there is nothing to note against.
