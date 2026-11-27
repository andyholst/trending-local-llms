# Proposal: issue-queue-thread-claim-1801

Issue: #1801
PR: #1802

## Why

`issue_queue.build` decides whether an issue already has an implementer solely from branch refs
(`ci/data-gap-<n>-*`) and open PRs. A host fleet lane claims an issue on the ISSUE thread with a
signed `BOT <lane> · working on #<n>` marker (rules 6u/7b) before it cuts a branch. During that
window the claim is invisible to the automated issue-bot sweep, so a sweep whose `pick` falls
inside it selects the SAME issue and opens a second, conflicting delivery. Measured on
2026-11-27: #1798 was claimed at 09:52:58Z; the host PR #1799 and the issue-bot PR #1800 were
both opened minutes later, each carrying `Closes #1798`.

## What Changes

- `scripts/issue_queue.py` reuses the ONE claim parser in `scripts/dispatch_guard.py`
  (`comment_markers` through `normalize_comments`/`active_claim`) to read signed thread claims.
- An ACTIVE, fresh (inside `gap_hours`) `working on #<n>` claim counts as an implementer: the
  issue is skipped from the sweep's pick order, exactly like a branch or an open closing PR.
- A stale claim (older than the window) or one cleared by a release marker (`done` / `pr` /
  `reviewing`) releases the issue, so a cancelled lane cannot park it for ever.
- A claim naming a different issue never hides this one.
- `tests/test_issue_queue_predicate.py` is extended with RED-proven guards.

## Impact

- The existing branch / open-PR / MERGED-PR predicates are unchanged.
- No new marker spelling: the claim grammar has ONE home (`dispatch_guard`), rule 6d.
- No credential, no workflow, no new make target.

## Not covered

- No `AGENTS.md` edit is made by this headless lane. The owed §8 guard row is declared blocked
  (`rule 3c human sign-off`) in `tasks.md` and filed as an owed-row finding for attended sign-off.
- No change to the reviewer's window logic or to `issue-bot`'s dispatch itself.
- No change to any pipeline shape.
