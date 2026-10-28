# When the sweep dies before its verdict, say so on the issue it picked

**Issue:** the sweep's own outcome comment — the half `a-fresh-red-sweep-is-loud` (#498) recorded as "Tracked separately"
**Capability:** `bot-coordination`

## Why

`issue-bot.yml`'s `implement` job only speaks on the issue it picked once it reaches a step that
OWNS a comment:

- `Apply the implementer's verdict` — comments for `refine` / `close`;
- `Report the outcome on the issue` — comments for `implement`, and is gated on
  `steps.verdict.outputs.verdict == 'implement'`.

So a sweep that STARTS and then dies before its verdict — the measured #120 / #281 / #346 class
(a resolver that could not read the issue, a checkout or base assertion that refused, an image or
smoke step that failed, an agent that wrote no `triage.md` so `make issue-verdict` exits 2) —
posts the start marker and then NOTHING. The issue shows "an implementer has started" for ever,
the red `implement` job lives only in the Actions tab (#488), and since #496 the sweep drains 48
open issues at one per delivery, so one dead run is a day of queue with no artifact on the queue
item itself.

The delivery half is already loud (`scripts/sweep_alarm.py`, #498: a fresh delivery whose
conclusion is not `success` is a verdict, not health). What is missing is the artifact a reader of
the ISSUE can see: what the sweep did, and that it stopped.

## What Changes

- **`scripts/sweep_outcome.py`** (new) — the decision and the composer, deterministic and pure
  where it matters: `owed()` says whether this run owes an outcome comment (it does NOT when the
  run implemented nothing, when the issue closed in flight — the already-fixed notice owns that —
  or when a verdict step already commented), `comment_body()` renders the one comment, and
  `--post` writes it through `gh issue comment` **once per run**, deduped on the run id.
- **`make issue-outcome`** — the only entry point (rule 6d/6m), so the command a bot runs and the
  command a human can run are the same.
- **`scripts/bot_markers.py`** — registers `issue-bot-outcome` (kind `outcome`) and lists it as
  WRITTEN, so the marker has ONE definition for the writer and any future reader (rule 6j).
- **`AGENTS.md`** §6j — the `issue-bot` row of the marker table names `issue-bot-outcome`, and
  §6e says a sweep that dies before its verdict posts its own outcome.
- **`.github/workflows/issue-bot.yml`** — one `always()` step at the end of `implement`, gated on
  `implement == 'true'`, the issue NOT closed in flight, and `verdict == ''` (so the verdict step
  and the outcome comment keep owning the paths that already work), which calls
  `make issue-outcome` with the run, the branch and the per-stage outcomes.
- **`ARCHITECTURE.md`** — the target, the script and the pipeline's step inventory.
- **`tests/test_sweep_outcome.py`** — the decision matrix, the marker round-trip, the dedup, the
  loud refusal, driven through the real script with a stub `gh` (an external system, never a
  mocked product symbol: rule 6m).
- **`tests/test_workflows.py`** — the shipped step: present, `always()`, gated so it cannot
  double-post, using the default token, calling the target, after the checkout and after the
  steps that own the other paths.

## Impact

`issue-bot`'s `implement` job gains one step and one comment per DEAD run. A run that reaches its
verdict posts exactly what it posted before; a run that implemented nothing, or found the issue
already closed, stays silent. No data change, no contract change, no new secret.

## Not covered (out of scope)

- **A sweep that dies before it PICKS an issue** (the `pick` job failing — the #547/#548 class).
  There is no issue to comment on; that failure is already loud through the red job, through
  `bot-health` (#488) and now through the delivery alarm (#498).
- **A cancelled run.** `concurrency: issue-bot-issue-<n>` cancels the queued run: a run cancelled
  mid-step executes no further step, so nothing can post from inside it. Same loudness as above.
- **The PR's own outcome comment** (`fix-bot` / `qa-validate`) — untouched.
