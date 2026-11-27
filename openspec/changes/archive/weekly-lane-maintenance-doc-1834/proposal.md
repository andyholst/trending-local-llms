# Proposal: weekly-lane-maintenance-doc-1834

Issue: #1834
PR: #1837

## Why

Measured at fetched base `453597d7`: issue #1834 asks for a weekly lane-maintenance pass that keeps
the four-per-lane fleet, its in-tree `agents/` mirrors and the canonical collaboration doc honest —
but only §6 of the companion doc (#1833 / PR #1836) sketched it, with no runnable checklist, no
exact per-host sync command and no drift-filing path. The owner directive 2026-11-27 requires a
cadence the planner runs when started, explicitly NOT a timer: no Hermes cron and no new GitHub
Actions `schedule:`.

## What Changes

- Add `docs/weekly-lane-maintenance.md`: the canonical five-step runnable checklist — fetch and
  run `make fleet-host-sync-check BASE=origin/master` from THIS host, verify the four-instance
  roster, verify the collaboration doc, post the board note, record the pass on issue #1834 —
  with an explicit cadence-not-timer statement and the drift-filing path (small `enhancement`
  issue, fixed through `tll-implementer` and the in-tree mirrors, never wiping Hermes runtime
  stamps or byte-copying host files).
- Add real guards in `tests/test_weekly_lane_maintenance_doc.py` that read the doc and fail when any
  stated obligation is removed. RED-proved on the first draft (6 failures) before the doc was
  corrected.
- Cross-link the canonical collaboration doc §6 to this checklist once companion PR #1836 lands
  that doc on `origin/master` — serialized, one writer per shared file.
- Track this work as this OpenSpec change and regenerate `OPENSPEC.md`.

## Impact

Docs and tests only. No `data/` change, no workflow, no cron, no new Actions schedule, no root
`AGENTS.md` edit, no hand-edit of the generated README tables. The pass reports drift; it does not
patch a lane or force a red host-sync check green.

## Not covered

- The pass is not run here: it is executed by a planner session the owner starts on each host.
- The in-tree `agents/` mirror refresh for the new standing behaviour stays with #696 /
  `tll-implementer`; this change only documents the check and the filing path.
- No second PR for #1833 — that issue is held by `tll-implementer` via PR #1836.
