# Proposal: queue-drops-run-backstop

Issue: #193 — `tech-debt: The in-flight backstop in the queue matches a run by its display title`

## Why

`scripts/issue_queue.py` held an issue when any `queued`/`in_progress` run's
`displayTitle` contained `#<n>`:

```python
in_flight = any(
    r.get("status") in ("queued", "in_progress")
    and f"#{number}" in (r.get("displayTitle") or "")
    ...
```

`displayTitle` cannot identify an issue. Measured on this repository
(`gh run list --workflow issue-bot.yml --limit 12`):

| event | displayTitle |
|---|---|
| `schedule` (the hourly sweep) | `issue-bot` — the workflow name, no issue |
| `issues` | the issue **title**, e.g. `tech-debt: The AGENTS.md §8 guard row for tests/test_ci_wiring.py is owed` — often no `#<n>` at all |

So the backstop never fired for a sweep, and fired only by accident for an `issues`
run whose title happened to contain the number — a run the implementer's start comment
already describes. It read as coverage (“a queued run whose start comment the reviewer
has not seen yet”) that did not exist, and it cost one `gh run list` call per queue
build.

## What Changes

- **The `displayTitle` backstop is deleted**, together with `_runs()` and its call: the
  implementer's START COMMENT is the one in-flight signal (AGENTS.md rule 6j — it is
  posted before `make implement-issue` reads the body, so it covers the whole run, and
  the reviewer's 3 h window is built around it).
- **`reason=run-in-flight` now means “a fresh start comment (or start activity)”**, not
  “a run title matched”; `started` follows the same signal.
- **`tests/test_issue_review.py::test_the_queue_attributes_a_run_by_its_start_comment_not_its_title`**
  feeds the queue an in-progress run whose title contains the issue number and an issue
  with no start comment: the issue must NOT be `started`, must not be
  `reason=run-in-flight`, and the queue must not call `gh run list`. A second case
  proves a fresh start comment still marks it started — the signal that replaced it.

Verified RED against the pre-change queue (3 failures: `started=1`,
`reason=run-in-flight`, and the `run list` call in the stub's log) and GREEN after
(`PASSED 70 | FAILED 0`).

## Impact

`scripts/issue_queue.py` (one helper deleted, one condition deleted), its test module,
this OpenSpec change and the regenerated `OPENSPEC.md`. The queue is the ONE rule both
bots read, so both get the corrected attribution; one fewer `gh` call per build. No
make target, stage, job or image changes (`ARCHITECTURE.md` unchanged, rule 6h).

## Not covered

- **A true in-flight backstop.** Before the start comment exists there is nothing in the
  API that maps a run to an issue (`inputs` are not in `gh run list`'s JSON, and a
  queued run has pushed no branch) — the start comment is written before the body is
  read precisely so this window is covered by design, not by inference.
- **The reviewer's own window** (`REVIEW_GAP_HOURS`) is untouched.
