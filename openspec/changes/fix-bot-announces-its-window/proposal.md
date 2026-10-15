# fix-bot announces its repair window on the PR (issue #198)

**Issue:** [#198](https://github.com/andyholst/trending-local-llms/issues/198)
**Capability:** `bot-coordination`

## Why

`fix-bot.yml` runs: `guard` → `Resolve PR` → `Checkout PR branch (PAT)` → `make image-ensure` →
`make hermes-smoke` → `scripts/fix_loop.sh` (check → `make fix` → re-check, ≤ `FIX_ROUNDS`) →
`Commit + push the fix (only when green)` → **`Report result on the PR`**. The run's ONE comment is
posted at the **end**. Everything before it is invisible on the PR.

The loop reads the branch and then pushes to it. Anyone reading that PR in between — a human, the
reviewer, or the next `qa-validate` run — sees a state that is about to change, and nothing on the
PR says a repair is in flight. This is the same "read once, then a rewrite makes the two texts
differ" race #179 pinned for the issue body, one artifact over.

Today the only way to answer *"is fix-bot working on this PR right now?"* is the Actions API, which
a reviewer reading the PR page cannot see.

## What Changes

- **`.github/workflows/fix-bot.yml`** — a new step, `Announce the window on the PR`, placed
  **between `Resolve PR` and `Checkout`**, so it lands before anything reads the branch. It posts
  ONE comment carrying `<!-- fix-bot-start: <ISO8601Z> run=<id> -->`, the branch and the run URL,
  using the **default `github.token`** (the owner PAT cannot comment — measured,
  `Resource not accessible by personal access token (addComment)` on #124), with `issues: write`
  added to the workflow's `permissions:` for exactly that. The body is piped on **stdin**
  (`gh pr comment --body-file -`), so no scratch file exists that the push step's `git add -A`
  could commit.
- **The window closes on every path.** The existing outcome comment already runs under
  `if: always()`; it now begins with `<!-- fix-bot-end: <ISO8601Z> run=<id> -->`, so a loop that
  died mid-way still ends with a timestamp and the PR never shows a repair as permanently in
  flight.
- **`scripts/bot_markers.py`** — `(fix-bot, start)` and `(fix-bot, end)` move from `DECLARED_BY`
  (no writer yet) to `WRITTEN`, so the registry's own test now requires a writer in the tree and
  `scripts/issue_queue.py` can read a fix-bot window the day it needs to.
- **`tests/test_workflows.py`** — `test_fix_bot_announces_its_window`: the step exists, precedes the
  checkout, carries the marker and the branch/run, uses the default token, and the close is in the
  `always()` outcome comment.
- `ARCHITECTURE.md`'s `fix` job row and `AGENTS.md`'s §6b fix-bot bullet + §8 row.

## Impact

One extra PR comment per fix-bot run, posted before the branch is touched. That is the point: the
window becomes readable where the reader already is. Nothing else changes — the loop, the push
gating, and the "never merge" behaviour are untouched, and the invocation is
`workflow_dispatch`-only with `concurrency` per PR, so this is a timestamp a reader interprets,
never a mutex.

## Not covered

- Making the window a lock — #198's own non-goal; `concurrency` already serialises runs per PR.
- `qa-validate`'s merge decision and its `bot-merge` row (registered, writer not yet landed).
- `refresh-bot`'s own window — that is **#199**.
