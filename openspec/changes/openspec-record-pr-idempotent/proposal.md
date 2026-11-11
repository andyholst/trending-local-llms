# Proposal: openspec-record-pr-idempotent

Issue: #754 (tech-debt, "openspec-record-pr is not idempotent: a re-run on an
already-archived change fails loudly instead of being a no-op")

## Why

`scripts/openspec_record_pr.py` (from #518) records the completing PR on a
change and archives it, once, per change. But bot pipelines are re-run — a
re-dispatch, a retried failure, a fix-loop push that re-triggers the implementing
run — so an already-archived change is the *expected* state on a re-run.

The script was not idempotent: `record()` iterates ACTIVE changes only, so once
a change had been archived by an earlier run it was no longer matched, and the
"no active match" path raised `NoSuchChange` → exit 2 — a benign re-run turned
into a run that looked like it failed mid-implementation. The docstring promised
an `AlreadyThere` case, but no such class existed.

Measured on `master` (evidence, #754): `scripts/openspec_record_pr.py:81-82`
says it "raises `AlreadyThere` when every match is already archived", but only
`NoSuchChange` is defined (line 51), and `record()` reads `_active_changes`
(lines 87/104). A re-run could not tell "never matched" (a real defect worth
refusing) from "already done" (a benign no-op), so every re-run went red.

## What Changes

- **`scripts/openspec_record_pr.py`** gains an `AlreadyThere` exception and a
  second prong in `record()`: after no ACTIVE change matches, it looks at the
  ARCHIVED changes for the same `Issue:` — if one exists the recording already
  happened, so it raises `AlreadyThere`; `main()` catches that and exits **0**
  naming the change as already recorded, without editing the archive. Only when
  no change (active *or* archived) references the issue does it still `REFUSE`
  with exit 2.
- **`tests/test_openspec_record_pr.py`** adds `test_rerun_on_an_already_archived_change_is_a_noop`:
  a second run after archiving exits 0, re-creates no active change, does not
  edit the archive, and names the change as already recorded; the existing
  "no change names the issue → exit 2" test is unchanged.

## Impact

- `make openspec-record-pr` becomes safe to re-run: the `issue-bot.yml` step that
  runs it right after `gh pr create` no longer reds a run that was merely
  re-dispatched or re-tried.
- No data, contract, README table, make target, workflow or image changes.

## Not covered

- The guard's own `make openspec-archive-check` behaviour is unchanged; this
  change is only about the reverse, `openspec-record-pr`.
- Whether an archived change's `PR:` line differs from the number passed on a
  re-run is not asserted — the no-op accepts the archived state as recorded.
