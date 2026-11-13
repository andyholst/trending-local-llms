# Proposal: archive-stranded-completed-changes-907

Issue: #907 (referenced — this keeper records the drift it lands; it does not implement code)

## Why

`OPENSPEC.md` lists five **active** changes — `land-the-owed-rulebook-rows` (12/12),
`the-owed-section-8-rows` (8/8), `captured-recipe-is-silent` (6/6), `one-queue-reader`
(12/12), `index-failure-names-its-cause` (9/9) — every task box ticked, while the issues
they name (391, 400, 310, 322, 324, 314, 212, 380, 385, 405, 543, 547, 548) are all CLOSED.
They landed before issue #866's `make openspec-archive-check` existed (which now refuses a
merge that strands the change it closes), so they are the recorded-but-UNarchived shape: the
active list misstates what is in flight and a reader cannot tell "shipped, archive missed"
from "still open work". The same drift was last repaired the same way, by
`archive-stranded-completed-changes` (archived 2026-11-12).

## What Changes

- The five completed changes are archived with `make openspec-archive NAME=<change>` (their
  specs are landed and pinned in `tests/`).
- This keeper run is recorded as its own tracked change and archived in the same commit
  (precedent shape).
- `OPENSPEC.md` regenerated (`make openspec-index`); the index stays current.

## Impact

`openspec/changes/` (five moves + this change's own archive) and the generated `OPENSPEC.md`
index. No code, target, stage, job or image changes; `ARCHITECTURE.md` untouched (nothing moved).

## Not covered

- Extending the archive-check sweep to master state (the second `Done when:` half of #907) —
  #866's gate already blocks NEW stranding at the PR; a master-state reporter is separate work.
- Any change whose tasks are not fully ticked — none of the five is touched beyond the archive
  move, and no active change is archived that still has unticked boxes.
