# Proposal: archive-check-gates-the-closing-pr

Issue: #779 (measured: qa-validate runs 43014075519 after PR #777 merged,
43028760218 and 43030796045 after PRs #778/#781 merged — all three master pushes
red on `[archive-check] FAIL — no active OpenSpec change may name a merged PR`)

## Why

Rule 6f says a merged change lands archived with `PR: #<n>`, and
`make openspec-archive-check` is supposed to make that true. It reads GitHub
state for changes that ALREADY carry a `PR:` line, or reports a closed issue
with no line — after the merge. Both prongs are therefore AFTER-THE-FACT: on a
pull request they read vacuously green, because at check time the issue is
still open and no PR line is expected yet. Measured twice in one day: PR #777
merged leaving `master-alarm-push-signal` active, then PR #781 merged leaving
`ban-pytest-imports-in-tests` (Issue: #768) active with no `PR:` ever recorded
— each time `openspec-archive-check` went RED on the master push and every
open PR's `validate` blocked behind it.

Why #781's branch never archived: its implementer ran issue-bot run 42811107133
(2026-11-10 11:53Z), whose copy of `issue-bot.yml` predated the
`make openspec-record-pr` step (#776 merged 2026-11-11 06:41Z). A PR cut from
an older base runs the OLD pipeline; nothing in the PR's own CI noticed the
missing lifecycle step, so the change reached master unarchived.

## What Changes

- `scripts/openspec_archive_check.py` gains a THIRD prong: `--pr <n>` reads
  THIS pull request's title+body, extracts its closing issues through
  `scripts/pr_closure.py`'s own parser (one closing-keyword implementation,
  rule 6d), and fails any ACTIVE change whose `Issue:` names one of those
  issues without naming this PR. The PR that closes a change's issue must
  archive it IN ITS HEAD — a change the old pipeline forgot is caught before
  merge, not after.
- `make openspec-archive-check PR=<n>` (flag forwarded) and `qa-validate.yml`
  passes the pull request number on `pull_request` events; push/dispatch runs
  keep the existing two prongs unchanged.
- The stranded change `ban-pytest-imports-in-tests` (#768, PR #781 merged) is
  recorded with `make openspec-record-pr ISSUE=768 PR=781` and archived in
  this branch, clearing master's red.

## Not covered

- Publishing a multi-arch OpenSpec image so arm64 hosts can pull it (issue
  #767 tracks that separately).
- Changing the implementer workflow itself: the record step from #776 already
  exists on `master`; this change makes every PR prove its head ran it.

## Impact

- Capability spec: `openspec-archive-lifecycle` (new requirement: the closing
  PR prong).
- `qa-validate` `validate` job: one existing step gains the `PR=` argument.
- Bot PRs gain one expected transient: `record-pr` pushes a second head
  (archived change + index), which is the head `auto-merge` merges.
