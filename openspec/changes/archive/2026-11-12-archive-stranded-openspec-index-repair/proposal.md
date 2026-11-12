# Archive the completed change PR #859 left active

**Issue:** #864
PR: #865

## Why

`make openspec-archive-check` is red on the master push (measured on qa-validate
run 43269076958, head 24c6675 = PR #859's squash merge): the OpenSpec change
`openspec-index-repair` — implemented and merged as PR #859 — is still ACTIVE
in `openspec/changes/`. A merged-but-active change reds the `validate` gate on
every push to master AND on every open PR that inherits the tree (its own
repository-scan test `test_the_repository_itself_has_no_merged_change_left_active`
fails too), until an archive lands — the same repair #774/#775, #779/#780 and
#851 each had to make once.

## What Changes

- `make openspec-archive NAME=openspec-index-repair` moves the completed change
  to `openspec/changes/archive/2026-11-12-openspec-index-repair/` (moved, never
  deleted — rule 3b) and promotes its `openspec-index` spec delta into
  `openspec/specs/openspec-index/spec.md`.
- This repair is recorded as its own tracked OpenSpec change
  (`archive-stranded-openspec-index-repair`, proposal + spec delta + tasks),
  archived in the SAME commit: an active archive-repair change naming this very
  PR would manufacture the next recurrence (#780/#851 pattern).
- `make openspec-index` regenerates `OPENSPEC.md`.

## Impact

- Affected specs: `openspec-index` (the stranded delta is promoted),
  `archived-change-lifecycle` (this change's new requirement).
- Affected code: none — archive bookkeeping only.
- Unblocks the master `validate` run and the open PRs #862 (and any later PR)
  that fail only because they inherit this red gate from the base.

## Not covered

- WHY the merge of #859 did not archive its own change even though rule 6f's
  archive-check gate exists on the PR side (the auto-merge lands the squash
  before the after-the-fact archive commit — the recurrence keeps arriving
  through this seam) — that guard gap is analysis for a separate reviewed
  change, not this one.
