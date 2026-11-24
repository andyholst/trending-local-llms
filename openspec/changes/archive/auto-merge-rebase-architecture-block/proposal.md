# Proposal: auto-merge-rebase-architecture-block

Issue: #1601
PR: #1603

## Why

`make auto-merge-rebase` (the pre-squash gate, issue #1049) regenerates **`OPENSPEC.md`** on the
rebased tree but not `ARCHITECTURE.md`. When a bot branch is behind master and BOTH generated files
conflict, the rebase aborts on the `ARCHITECTURE.md` conflict, so the branch stays unmergeable until
a lane resolves both by hand — measured on 2026-11-24 (`fix/os-agnostic-make-cross-cutting-seams-1496`,
run `45376351524`; `tll-pr-draft-ready-1563`, PR #1570):

```text
$ git diff --name-only --diff-filter=U
ARCHITECTURE.md
OPENSPEC.md
```

The same rebase has to satisfy `make architecture-check`, whose §10 inventory block is generated into
`ARCHITECTURE.md` by `scripts/architecture_bot.py` — a head that is current for one generated file and
stale for the other is not a validated head.

## What Changes

- `scripts/pr_health.py` gains `regenerate_architecture(wt)` beside `regenerate_index(wt)`, and
  `rebase_and_push` refreshes BOTH generated artifacts on the rebased tree before the `--force-with-lease`
  push — each through the tree's OWN generator (rule 6d: never a second implementation).
- A rebase whose ONLY unmerged paths are `OPENSPEC.md` and/or `ARCHITECTURE.md` resolves those two by
  taking the branch's side and continuing, then regenerates both; a conflict anywhere else still aborts
  and leaves the remote branch byte-identical (the fix-loop/human partition, rule 6s).
- `scripts/auto_merge_rebase.py` names both artifacts in its verdict text.
- RED-first guards in `tests/test_auto_merge_rebase.py`: a clean rebase refreshes the architecture
  block too, and a both-files conflict lands a head where both gates are green.
- The analysis is recorded in the per-issue `findings/1601.md` (issue #1493's seam).

## Impact

Additive behaviour inside the existing bot-owned, clean-branch partition only. The human-owned,
conflicting and draft partitions (#1089/#1295) are untouched. No data format, contract, image or
workflow wiring change; the branch shape and the auto-merge `if:` are unchanged.

## Not covered

- A conflict outside the two generated files (still aborted, announced, handed to the fix loop/human).
- Any change to `make architecture-refresh`, `scripts/architecture_bot.py` or the keepers' own flow.
- No CI dispatch, no merge, no master push, no new cron.
