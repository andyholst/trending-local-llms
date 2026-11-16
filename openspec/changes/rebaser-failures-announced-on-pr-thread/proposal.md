# Proposal: rebaser-failures-announced-on-pr-thread

Issue: #964

## Why

`scripts/pr_health.py::run_rebaser` prints `rebaser #N <branch>: kept: <reason>`
to stdout only; the only writer of PR comments (`--comment`, gated by
`findings()`) covers SILENT PRs exclusively. A behind bot branch whose rebase
git REJECTS (a conflict git sees before GitHub labels the PR CONFLICTING, a
failed lease push, unreadable refs) therefore leaves no artifact on the PR
thread — the sweep rediscovers it every week, attempts the same failing rebase,
and the only trace is one line in a scheduled run's log. That is the "quiet
queue" failure class `pr-health.yml` exists to make loud (issue #964's measured
end-to-end run).

## What Changes

- The rebaser's ATTEMPTED-AND-FAILED outcomes (anything under the
  `rebase-if-behind` plan action that did not end `REBASED:`/`already current`)
  are announced on the affected PR's thread when `--comment` is on, through the
  script's existing comment path.
- A NEW registered marker `pr-health-rebase-failed` (registered in
  `scripts/bot_markers.py` REGISTRY/WRITTEN/ARTIFACTS, rule 6j, with its
  AGENTS.md §6j table row landing in the same change) stamps each announcement
  with the branch and the head oid it failed on: one announcement per failed
  (branch, head) round — a re-run of the same round does NOT double-post, and a
  branch whose head moves may be announced again.
- `pr_health.py` stops spelling its marker literals privately: `MARKER` and the
  new rebase marker come from `bot_markers.marker_name` (rule 6j: one
  definition).
- The comment names the failure reason and the concrete remedy
  (`make worktree-resume`, `make base-rebase`, and that conflict resolution
  belongs to the PR's own fix loop or a human — rule 6s' partition).

## Impact

- `scripts/pr_health.py` — announce loop after `run_rebaser`, marker import,
  comment body builder (no new make target; `make pr-health` and
  `pr-health.yml`'s `COMMENT=1 REBASE=1` call are unchanged).
- `scripts/bot_markers.py` — the `pr-health` bot family enters REGISTRY,
  WRITTEN and ARTIFACTS (both markers, alarm + rebase-failed).
- `tests/test_pr_health.py` — new end-to-end test: a planted git-conflicting
  bot branch with `--rebase --comment` posts ONE marker-deduplicated comment;
  the next round seeing the same marker on the thread stays silent; the branch
  stays byte-identical (the rebaser still never force-pushes a conflict).
- `AGENTS.md` §6j table gains the `pr-health` row; §8 gains the guard row.

## Not covered

- Exit-code semantics of a failed rebaser round stay as they are (the silent-PR
  verdict decides exit 1; this change makes the THREAD loud, per the issue's
  Done-when).
- Auto-resolving conflicted branches — rule 6s reserves that for the PR's own
  fix loop or a human.
