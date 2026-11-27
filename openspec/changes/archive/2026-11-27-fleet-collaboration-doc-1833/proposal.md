# Proposal: fleet-collaboration-doc-1833

Issue: #1833

## Why

The owner directed (2026-11-27) that the tll fleet must document in detail how the bots work
together and each lane's responsibility. Measured at base `525185378c39`: `agents/README.md`
is an 18-line table with no workflow, no claim/handover protocol and no concurrency rule. The
real collaboration rules live only in the planner skill and eight per-lane SOUL/SKILL files,
with no canonical reader-facing document and no cross-link between them. With the fleet scaling
to four instances per delegable lane, a second source of truth is a correctness problem: clones
on different hosts would follow different protocols and claim the same issue.

## What Changes

- Add `docs/fleet-collaboration.md`: the canonical collaboration + responsibility document,
  covering the owner start, the issue-thread board, all eight lanes and their remits, the exact
  signed claim/dispatch/pr/reviewing/done formats, four instances per delegable lane with the
  dispatch ceiling and claim-twice race guard, and the weekly cadence-not-timer maintenance pass.
- Add one cross-link from `agents/README.md` to that document, so the short table points at the
  canonical doc instead of competing with it.
- Extend the already-rowed `tests/test_fleet_lifecycle.py` with three guards: the doc covers the
  board protocol and every lane, the README cross-links it, and the weekly pass is kept distinct
  from a cron/timer. Register all three in that module's `main()` (the test image discovers the
  module by the `test_*.py` glob).
- Add this tracked change (proposal, one capability spec with Given/When/Then scenarios whose
  `Test:` lines name those three real functions, and a ticked task checklist) and regenerate
  `OPENSPEC.md`.

## Impact

Purely additive documentation plus a source-level guard: no data, schema, contract, Makefile,
workflow, script or rulebook edit. No existing key, value or rule is removed or narrowed, and
no new `make` target, stage, pipeline job or image is introduced, so `ARCHITECTURE.md` needs no
change. `AGENTS.md` is not edited in this headless leg; the owed extension of its existing §8
row for the three new guard functions is recorded in `findings/1833.md` and is review-required
(rule 3c). Disjoint from companion #1834 (the weekly-pass checklist) and from the in-flight
#1797/#1830 work.

## Not covered

- No rulebook change, no new cron or Actions `schedule:`, no host profile rewrite, no CI
  dispatch, no merge and no push to the base branch. Companion #1834 remains a separate issue
  and PR; this doc only links the pass it defines.
