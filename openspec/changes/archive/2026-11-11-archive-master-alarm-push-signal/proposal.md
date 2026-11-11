# Proposal: archive-master-alarm-push-signal

Issue: #779 (measured: `openspec_archive_check.py` on `origin/master` at fc16962 flags `master-alarm-push-signal` — issue #527 closed, no `PR:` line recorded, PR #777 merged)

## Why

`make openspec-archive-check` (rule 6f/#513) fails when an ACTIVE change names a
merged PR or a closed issue with no `PR:` line. `master-alarm-push-signal` — the
OpenSpec change of PR #777 (issue-bot, issue #527) — merged and stayed active:
qa-validate run 43014075519 reds `master` at the OpenSpec gate, and every PR
rebased onto that master inherits a red `validate` job until an archive lands
(#774/#775 had to do exactly this once already).

## What Changes

- `make openspec-archive NAME=master-alarm-push-signal` — the change moves to
  `openspec/changes/archive/2026-11-11-master-alarm-push-signal/` (content
  unchanged, rule 3b: nothing removed).
- The tracked change of THIS archive (`archive-master-alarm-push-signal`) is
  archived in the same commit: its work is fully done on this branch, and an
  active change naming a merged PR is the next recurrence of the very red this
  PR removes. (Precedent: `2026-11-11-archive-record-pr-774`, #774's archive.)
- `make openspec-index` regenerates `OPENSPEC.md`.

## Impact

- `openspec/changes/` (two moves), `OPENSPEC.md`
- No code, no data, no pipeline change.

## Not covered

- WHY the issue-bot's `Record the PR on the change` step (issue-bot.yml) left
  `master-alarm-push-signal` with no `PR:` line, and a guard that the
  implementer's own change is archived before its PR merges — that is the
  (b)-half of issue #779 and its own reviewed change.
