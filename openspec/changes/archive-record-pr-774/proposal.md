# Archive the merged-but-unarchived record-the-pr-on-a-change change

**Issue:** [#774](https://github.com/andyholst/trending-local-llms/issues/774)
**Capability:** `archived-change-lifecycle`

## Why

PR #753 implemented issue #518 (`record-the-pr-on-a-change`) and merged it on
`master` tip `5c580e4`, closing #518. But the completing PR never recorded its
own `PR:` line on that change nor moved the change to
`openspec/changes/archive/record-the-pr-on-a-change/`. The lifecycle guard
(`scripts/openspec_archive_check.py`, rules 6f/#513) therefore reports red on
**master itself**:

```
[archive-check] FAIL 1 active change(s) ... record-the-pr-on-a-change — issue #518 is
closed but no `PR:` line was ever recorded ... run `make openspec-archive NAME=record-
the-pr-on-a-change` and `make openspec-index`
```

`make openspec-archive-check` is a hard step of `qa-validate`'s `validate` job, so
this red blocks auto-merge of **every** open PR — the whole bot fleet — until the
merged change is archived. This is the change that re-runs the lifecycle
completion the guard demands, in its own reviewed PR (rule 6g: a finding is
never folded into the change that found it).

## What Changes

- `openspec/changes/record-the-pr-on-a-change/` → archived under
  `openspec/changes/archive/record-the-pr-on-a-change/` via the OpenSpec CLI
  (`make openspec-archive NAME=record-the-pr-on-a-change`, Makefile:315). The
  change is complete (issue #518 done, merged) so archiving is the correct
  lifecycle state — it is never deleted, only moved to the archive ring.
- `OPENSPEC.md` regenerated (`make openspec-index`) so the root index lists the
  change under `archive/`, not the active table.
- A regression guard proving a merged-but-active change is refused by the
  archive check (so a future completing PR cannot silently leave its own change
  active and red the fleet). The existing checker already covers this class
  (issue #513); the guard is the same `openspec-archive-check` gate, verified
  green after this change.

**Not covered:** no change to the archive checker's logic, no change to
`openspec-record-pr` (that idempotency defect is issue #754, tracked
separately), and no deletion of any change or value (rule 3b — additive-only;
archiving MOVES a completed change, it never removes it).

## Impact

`make openspec-archive-check` (and therefore `make validate` and every open
PR's `validate` gate) turns green on `master` again. The bot fleet's data-gap,
tech-debt, review and refresh lanes can auto-merge once more. The completed
`record-the-pr-on-a-change` row no longer claims to be a live active candidate
in the index.

## Not covered

Implementing issue #754 (`openspec-record-pr` idempotency) was NOT done here
even though #753's missing `PR:` line is the immediate cause of the red — that
is its own tracked defect. This change only completes the lifecycle the guard
already enforces; it does not redesign the recorder.
