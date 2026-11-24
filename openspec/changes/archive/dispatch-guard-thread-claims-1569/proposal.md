# Proposal: dispatch-guard-thread-claims-1569

Issue: #1569
PR: #1572

## Why

Measured 2026-11-24: three hosts now dispatch this board (`asimov@mac`, `asimov@omarchy`,
`andy@Andys-MacBook-Pro`) and duplicate PRs result — #1562 vs #1564 for #1560 within one
hour, and #1445/#1449 vs #1448 earlier. Issue #1558 records two hosts claiming #1495 eight
seconds apart inside one watch cycle. `scripts/dispatch_guard.py` (#1416/#1458/#1460) bounds
collisions through a CALLER-OWNED registry OUTSIDE the repository, so it is per-host by
construction: host B cannot see host A's active lane at all.

## What Changes

- Extend `scripts/dispatch_guard.py`, do not rewrite it: `make dispatch-check ISSUE=<n>` (and
  `--claim`) additionally reads the issue's COMMENTS — the one surface every host shares —
  and refuses when ANOTHER host holds a NEWER ACTIVE working-claim on that issue. The signed
  markers `BOT <lane> · working on #<id>` / `· dispatch #<id>` are parsed with their machine
  line (`user@host`) and `createdAt`; a later `done`/`pr`/`reviewing` releases the claim.
- The refusal names the holding host, lane and comment id. A caller whose OWN marker is the
  newest is ALLOWED to re-dispatch. A claim whose host cannot be read does not block (the
  guard refuses a DIFFERENT, NAMED host; it never invents one).
- Keep EVERY existing refusal intact — closed issue, merged bound PR, `ACTIVE_LANE_CEILING`,
  the in-repo registry, and the #1458 `--claim`/`CLAIMS` overlap. This is an ADDITIONAL
  refusal, consulted alongside them.
- Fixture-test the parsing offline with recorded threads (`--comments-file`, or a `comments`
  list inside `--from-file`): no network, no credential values.

## Impact

Additive and read-only: no schema, contract, API, table, data shape or CI gate changes. The
guard still decides and never spawns a lane; it writes nothing and merges nothing. Live mode
reads the thread through `gh api --paginate --slurp`; `--from-file` callers (tests, a dry-run
host) keep working and default to an empty thread, so the pre-#1569 behaviour is unchanged
for them. No schedule is added or edited, and no protected instruction file is touched.

## Not covered

- No writer-side change: the guard reads the markers the fleet already posts; it does not
  rewrite any lane's claim, dispatch or handover text.
- No planner/watch-monitor/registry-writer change, no GitHub write, no label change, no new
  cron or workflow schedule.
