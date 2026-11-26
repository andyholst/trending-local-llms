# Proposal: parallel-planner-dispatch

Issue: #1767
PR: #1769

## Why

Issue #1767 records the owner's 2026-11-26 directive: the board must not be drained one issue at a time. The planner already starts lanes itself, but its documented contract still leads with serial habits in the SOUL mirror and has no per-lane accountability for a concurrent burst. Without an explicit contract, three simultaneous implementer lanes can race on one issue, share a branch, skip the signed issue-thread bookend, or be dispatched onto a tech-debt / protected-rulebook issue without a human decision.

## What Changes

- Add a `Parallel implementer dispatch (owner directive, issue #1767)` section to `agents/tll-planner/skills/tll-planner/SKILL.md`: up to 3 implementer lanes CONCURRENTLY against DISTINCT open issues; serialise only a genuine shared-file collision through `make dispatch-check ... CLAIMS=`.
- Spell out one query file, one signed issue claim (twice-claim race guard), one worktree off the fetched `origin/master`, one lease-checked branch pinned with `--force-with-lease`, and one board-visible start+done bookend per lane.
- Forbid dispatch onto tech-debt or protected-rulebook work without explicit owner sign-off, and restate that the planner neither merges nor pushes to master.
- Add `tests/test_parallel_planner_dispatch.py`: a source-level guard that is RED on the fetched base skill (all 10 clauses absent) and GREEN on this head, wired into `main()` and discovered by the one runner.
- Record the rule-3c owed rows in `findings/1767-planner.md`: the §8 guard row and the protected SOUL mirror.

## Impact

Documentation and a new source-level test only. No production script, data store, workflow schedule, credential or lane profile outside the named scope is changed. The planner still writes no tree; qa-validate alone merges green heads. The protected `agents/tll-planner/SOUL.md` mirror is declared owed rather than force-written.

## Not covered

- No merge, no push to master, no closing of #1767, no cron, no Actions `schedule:` edit, no edit to `AGENTS.md` or another lane's files.
