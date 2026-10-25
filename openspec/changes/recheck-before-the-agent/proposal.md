# The issue's state is re-read immediately before the agent starts

**Issue:** [#522](https://github.com/andyholst/trending-local-llms/issues/522)
**Capability:** `issue-implementer`

## Why

The sweep picks an issue ONCE, at the start of the `pick` job, and the implement job then
spends minutes on setup: checkout, base assertion, image preparation, the Hermes smoke, the
whole-thread read, the window announcement. `auto-merge` lands PRs continuously, so an issue
picked at T can be closed at T+8m by its own PR — and the run then implements an issue that
no longer exists.

Measured twice: run 39612330011 (#183 picked 14:37, PR merged 14:38, run ended red at 14:41)
and again today on run 40199055887, where `pick` chose **#362** whose PR #557 was already
open. The only state read before the agent is on `master` in the FAIL-LOUD step, i.e. at
step 19 — AFTER the agent at step 7. `make issue-state` exists and is correct; it is simply
asked too late to save anything.

## What Changes

- **`.github/workflows/issue-bot.yml`** — a `Re-read the issue's state right before the agent
  starts` step (`id: recheck`), placed directly before `Implement the issue`, after the
  checkout (rule 6d: a `make` target needs the repo):
  - exit 4 (closed) → the same `issue-bot-already-fixed` comment the fail-loud step posts,
    the step ends 0, and `closed=true` is published so no later step spends anything;
  - exit 2 (unreadable) → `::error::` and exit 1, because a state we cannot read is never a
    pass (the #520 contract);
  - exit 0 (open) → `closed=false`.
- `Implement the issue`, `Apply the implementer's verdict`, `Did the agent leave work behind?`,
  `Report the outcome` and `Fail loudly when the implementation did not happen` are all gated
  on `steps.recheck.outputs.closed != 'true'`, so a closed issue ends GREEN and quiet instead
  of red or half-done.
- **`tests/test_workflows.py`** — `test_the_issue_is_re_read_right_before_the_agent_starts`:
  the step exists, sits immediately before the agent and after the checkout, carries both
  exit-code contracts, publishes both outputs, and every spend/report step is gated.
- **`AGENTS.md`** §8 — the row is owed where the protected-file gate refuses the write; the
  exact text is in `findings.md`.

## Impact

The implement job's step order and five `if:` conditions. A run whose issue is still open is
unchanged; a run whose issue closed during setup now costs one `gh` read instead of 20-30
minutes and a red pipeline.

## Not covered (out of scope)

- The `pick` job still reads the queue once; a second read there would halve the window but
  costs a full API sweep per run. The cheap read sits where the spend begins.
- A closed issue still leaves the branch and any pushed commits alone — deleting them is a
  separate decision.
