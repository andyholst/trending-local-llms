# Proposal: dispatch-guard-1416

Issue: #1416
PR: #1428

## Why

Measured on asimov@mac 2026-11-23: **7 concurrent `tll-implementer` lanes** on one host —
load average 7.08, `Virtualization.framework` at 348% CPU on one shared container VM, lane
runtimes 128/94/76/70/66 min. Two were duplicate work: #1239 ran 95 min on an issue that
was already **CLOSED** (PR #1242 merged 13:19:42Z as `58469c00`, and its merge-tree step
already sits in `origin/master:.github/workflows/qa-validate.yml`), and #1250 stacked on
#1246/#1247 and became add/add conflicts when #1247 merged. Nothing refused a dispatch
whose target was already closed or whose PR had already merged, and nothing bounded how
many lanes a planner could spawn at once.

## What Changes

- Add `scripts/dispatch_guard.py`: ONE implementation of (1) the stale-target guard —
  refuse when the issue is CLOSED or when a PR bound to it (`closingIssuesReferences` or
  the implementer's `-<issue>` branch convention) is already MERGED — and (2) the
  concurrency bound — read a caller-owned active-lane registry **outside the repository**
  and refuse above ONE constant `ACTIVE_LANE_CEILING` (default 3), always printing the
  count. A path that resolves inside the tree is refused, matching the watch monitor's
  `--state` rule.
- Add `make dispatch-check ISSUE=<n>` as the planner's/watcher's ONE seam, forwarding
  `REGISTRY=`, `CEILING=`, `REPO=`, `FROM_FILE=` and `JSON=`. It exits non-zero with the
  reason on refusal; an undecidable read exits 2, never a silent clean.
- Add `tests/test_dispatch_guard.py`: fixture tests over the REAL decision functions,
  CLI and make target for open / closed / merged-PR / at-ceiling / over-ceiling, plus the
  in-repo registry refusal and `--help`. No network; no credential values.
- Add the target, script and guard rows to `ARCHITECTURE.md` via `make architecture-refresh`;
  keep `OPENSPEC.md` current with `make openspec-index`.

## Impact

Additive and read-only: no schema, contract, workflow schedule, data shape or CI gate
changes. No lane is spawned by the guard, no cron is added, no merge or master push. The
caller owns the registry's lifecycle; the guard only reads it. A dispatch without a
caller-owned registry is undecidable (exit 2), never a guessed "0 lanes allowed".

## Not covered

- No change to the planner's delegation rules or to the existing watch monitor.
- No registry WRITER: the fleet owner creates and updates the external file.
- No GitHub API write, no label change, no issue comment by the guard itself.
