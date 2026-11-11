# The implementer honours the reviewer's verdict

**Issue:** [#200](https://github.com/andyholst/trending-local-llms/issues/200)
**Capability:** `bot-coordination` (extends `issue-review`, issue #179)

## Why

Three bots share one issue queue — the filer (`refresh-bot`), the reviewer
(`issue-review-bot`, cron `41 * * * *`) and the implementer (`issue-bot` sweep,
cron `19 * * * *`) — and #179 gave them ONE queue rule (`scripts/issue_queue.py`,
`make issue-queue`) plus a 3 h window so the reviewer never rewrites a body an
implementer's run has already read.

That rule has a hole. The reviewer's **verdict** — the label it sets when it
judges an issue `needs-refinement` (and the `obsolete` / `duplicate` /
`already-fixed` family) — is computed by the queue and then only *reported*
(`reviewer_label`): `pick` order ignores it. The reviewer clears the label when
its refinement lands, so the common case works; the case that does not is the
label that **outlives its run** — a review that ended as "needs refinement" with
no rewrite (the agent could not produce a better body in the run, the run was
cancelled, a human set the label). Those issues stay exactly as
implementable-looking as before, and the next hourly sweep implements an issue a
reviewer has explicitly called not ready.

The reason the label was advisory is sound and must be kept: **a label carries no
timestamp**, so trusting it blindly would let a stale label stall the queue for
ever. The fix is not to trust the label — it is to date it from the marker
comment the reviewer already writes.

## What Changes

- **A verdict is a hold while it is FRESH.** `scripts/issue_queue.py` gains the
  verdict labels as a hold alongside the existing window hold: the label present
  **and** the newest reviewer marker comment on the issue (`<!-- issue-review: … -->`,
  including a window reply — the reviewer spoke) younger than `VERDICT_TTL_HOURS`
  (24). The row carries `verdict`, `verdict_since`, `verdict_fresh`; a fresh
  verdict sets `impl_skip=1`, `reason=verdict-fresh`, `position=-1`.
  - stale (marker older than the TTL) → released, the issue is back in the queue
    and the verdict is still reported;
  - no reviewer marker at all → reported, never a hold.
  The rule stays in the ONE implementation both bots read (`make issue-queue`);
  nothing about it moves into `issue-bot.yml`.
- **The implementer says so on the issue.** `scripts/issue_queue.py --skip-note`
  (`make issue-skip-note`), run by the sweep's `pick` job **only when the pick
  came back empty**, posts ONE comment on the held issue:
  `<!-- issue-bot-skip: <ISO8601Z> verdict=<label> since=<reviewer ts> -->` and the
  plain-language reason. Idempotent per review round (the marker carries the
  reviewer's own timestamp, so a second sweep in the same round says nothing).
- **The implementer never overrides a verdict.** Skipping is a **comment**: no
  label write, no body edit, on any path. The verdict belongs to the reviewer (or
  a human) — clearing it is theirs, and an expired hold simply returns the issue
  to the normal queue.
- **The token rule is unchanged and explicit:** the note uses the default token
  (`github.token`, which has `issues: write`); the owner PAT is scoped to
  Actions/Contents/Pull-requests and cannot comment.
- **Rule 6j** records the protocol in `AGENTS.md` (three verbs, one queue,
  timestamped markers, the same owner/collaborator `guard` first in every
  pipeline), `ARCHITECTURE.md` describes the new hold and the new target, and the
  README (through its template) explains it to a reader.

## Not covered

- The reviewer itself — that is #179 (`openspec/changes/issue-review-bot`),
  already merged (`2a1d7f4`).
- Automatically closing an issue when a verdict expires: the hold expires, the
  issue does not change state.
- Re-dating the `review-in-progress` label: it stays advisory exactly as #179
  shipped it (the window marker is what the queue reads).
