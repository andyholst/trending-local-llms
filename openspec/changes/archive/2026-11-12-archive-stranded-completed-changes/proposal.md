# Archive the two completed changes #845/#846 left active

## Why

`make openspec-archive-check` is red on every open PR (measured on qa-validate
run 43211996340 for PR #850, run 43209209465 for PR #819): the OpenSpec changes
`log-tail-honored` and `per-round-log-capture` — implemented and merged as PRs
#845 and #846 — are still ACTIVE in `openspec/changes/`. A merged-but-active
change reds the gate on every PR rebased onto this master until an archive
lands (#774/#775 and #779/#780 already had to do this once each).

## What Changes

- `make openspec-archive NAME=log-tail-honored` moves the completed change to
  `openspec/changes/archive/2026-11-12-log-tail-honored/` (moved, never
  deleted — rule 3b) and promotes its spec delta into `openspec/specs/`.
- `make openspec-archive NAME=per-round-log-capture` likewise moves it to
  `openspec/changes/archive/2026-11-12-per-round-log-capture/`.
- This repair is recorded as its own tracked OpenSpec change
  (`archive-stranded-completed-changes`, proposal + spec delta + tasks),
  archived in the SAME commit: an active archive-repair change naming this
  very PR would manufacture the next recurrence (#780 pattern).
- `make openspec-index` regenerates `OPENSPEC.md`.

## Impact

- Affected specs: `makefile-knobs` (log-tail-honored delta),
  `agent-log-capture` (per-round-log-capture delta).
- Affected code: none — archive bookkeeping only.
- Unblocks the `validate` job of the open PRs #850, #849 and #819, which fail
  only because they inherit this red gate from the base.

## Not covered

- WHY issue-bot's `Record the PR on a change` step left these two changes with
  no `PR:` line (the #779-class recurrence) — that guard gap is analysis for a
  separate reviewed change, not this one.
