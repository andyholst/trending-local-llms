# Proposal: bot-pr-rebaser-818

Issue: #818 — "Owner directive: an ACTIVE sweep must REBASE drifted bot PRs onto the
PR: #963
fetched base, not just report them" (the mechanical half of rule 6r's promise
"a PR that is CONFLICTING or behind its base is RESOLVED — not noted").

## Why

`make pr-health` has been report-only since #814: it flags a silent PR with a
comment and exits 1, but NOTHING in the pipeline ever rebases a drifted bot
branch. Measured: PR #439 sat `CONFLICTING` with zero workflow runs, and the
comment telling a human to run `worktree-resume` + `base-rebase` was the only
repair — while AGENTS.md §6r promised a bot PR "is repaired by the sweep". The
sweep already runs weekly (`pr-health.yml`), already reads every open PR with
its `mergeable`/`mergeStateStatus`, and already has a checkout: it is the one
place the rebase can land mechanically, with the §6r ownership partition intact
(a human's branch is still only reported).

## What Changes

- `scripts/pr_health.py`: a pure decision `rebase_plan()` (bot `ci/` prefix vs
  human; CONFLICTING never auto-rebased) plus a git execution half
  (`fetch_base`, `branch_behind`, `rebase_and_push`, `run_rebaser`) behind new
  flags `--rebase` / `--dir`. A rebase push is `--force-with-lease` pinned to
  the remote tip this run just fetched — a branch moved by someone else is
  never overwritten.
- `Makefile`: `_pr-health` / `pr-health` forward `REBASE=1` to `--rebase`.
- `.github/workflows/pr-health.yml`: the sweep step runs
  `make pr-health REPO=… COMMENT=1 REBASE=1`, the sweep job gains
  `contents: write`, and the checkout gains `fetch-depth: 0` (a shallow clone
  cannot rebase).
- `tests/test_pr_health.py`: plan-classification tests plus a REAL-git
  end-to-end (local bare origin + clone; only `gh` is stubbed) proving a
  behind-and-clean `ci/` branch is rebased with its own commit intact, and a
  human-owned branch, a CONFLICTING branch and master are byte-identical.
- `AGENTS.md` §6r + §6b (`pr-health.yml` bullet) + §8 guard row (rule 3c:
  this change updates the §6r mechanical-half line and the §6b pipeline bullet,
  because the sweep's contract changes from report-only to report-and-rebase).

## Impact

- Active rules: 6r (mechanical sweep half), 6d (decision in the script), 6m
  (Makefile-only path, real-git test), 6c (tests in the same change).
- Data: none. Pipelines: `pr-health.yml` sweep only.

## NOT covered

- Auto-resolving CONFLICTING bot PRs (conflict resolution stays the PR's own
  fix loop or a human — issue #818 Done-when: "a conflicted one is never
  rewritten").
- Rebasing human-owned branches (explicitly forbidden by §6r).
- Raising the sweep cadence (still weekly, Wednesday, per the cadence pin).
