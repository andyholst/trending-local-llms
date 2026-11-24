# Proposal: auto-merge-rebase-current-bot-regen

Issue: #1645

## Why

`make auto-merge-rebase` is qa-validate's pre-squash gate (issue #1049). It
regenerates `OPENSPEC.md` (and since #1601 `ARCHITECTURE.md`'s §10 block) before a
behind-and-clean BOT branch is pushed, so the squashed tree's generated files match
the tree they land into. A head that already CARRIES `origin/master` was reported
`current` and squashed unchanged. But carrying `master` does not make a generated
file current: a merge wave can archive a change while a PR waits, and the head's
committed `OPENSPEC.md` still renders the older tree. `make openspec-index-check`
only WARNs inside `MAX_OPENSPEC_INDEX_DRIFT` and exits 0, so the green squash lands
that tolerated drift and the #1634 index keeper repairs master minutes later
(measured live at `a0f9adc5`: `drift=1`, the count line said 527 while disk held 528).

The architect's design on #1645 answers two questions: (1) regenerate on a BYTE
difference between the committed generated pair and that tree's own `--write`
output — never key on the drift tolerance, which is deliberate gate slack (#1415);
(2) keep the §6s/#1089/#1295 human-owned refusal ABSOLUTE. A regeneration-only write
to a human's branch is a rewrite of it and falls inside that refusal; narrowing it
is an owner ruling, not an implementer's choice (Option B).

## What Changes

- `scripts/pr_health.py`: one shared core `sync_branch(cwd, head, *, rebase)` that
  creates the detached worktree at `refs/remotes/origin/<head>`, OPTIONALLY rebases
  onto the fetched master, then runs the existing `regenerate_index` and
  `regenerate_architecture` (both short-circuit when their file is already current)
  and lease-pushes only when a generator actually changed a file. `rebase_and_push`
  stays the ONE rebaser as the `rebase=True` wrapper; a thin `regenerate_current` is
  the `rebase=False` entry point. `_git`'s identity injection and the PAT push seam
  (issue #1115), including #1616's post-push CI proof, are reused unchanged.
- `scripts/auto_merge_rebase.py`: the `elif verdict == "current":` branch runs
  `regenerate_current(cwd, head)`; a landed regeneration prints `verdict=regenerated`
  and the SAME `rebased=true` squash-skip key, with the same #1616 CI proof. An
  already-current pair pushes nothing and stays `current`. `classify` is untouched:
  `current` and `behind-and-clean-bot` are returned only for a BOT-owned head, so a
  human-owned head stays report-only and byte-identical.
- `tests/test_auto_merge_rebase.py`: four real-git scenarios against a stub `gh`,
  RED on `origin/master`'s scripts.
- Rulebook (rule 3c, review-required): §6e and the §8 guard row gain the
  current-bot-head case; §6s stays byte-identical. `ARCHITECTURE.md`'s target, job,
  script and inventory rows are updated and the §10 block regenerated.

## Impact

No data, contract, README, workflow trigger, schedule, label or cron change. No new
make target, no second pusher, no change to `MAX_OPENSPEC_INDEX_DRIFT`, `--check`'s
WARN/exit codes, `--drift`, or the merge-tree gate. The only new behaviour is an
extra regeneration commit + CI round on a current bot head whose generated file is
measurably stale — the case that used to manufacture the drift.

## Not covered

- Narrowing the human-owned refusal (Option A) — owner ruling only.
- Fixing the already-merged drift on master — the §6q event-driven keeper owns that.
- Any change to the §6s wording or to the #1089 partition.
