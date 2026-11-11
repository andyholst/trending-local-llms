# Proposal: a-silent-pr-is-an-alarm

Issue: #442 (filed with two live measurements)

## Why

A PR whose merge commit GitHub cannot build (`CONFLICTING`) gets **no `pull_request` runs at
all** — `validate`, `live-smoke`, `pr-closure` and `auto-merge` are **absent**, not failed, so
`gh pr checks` answers `no checks reported` and the author sees an empty circle rather than a
red one. Measured:

- **PR #439**: zero workflow runs while conflicting (`gh run list` empty for the branch), for a
  PR that had merely fallen behind `master`;
- **PR #436**: green checks (`validate=SUCCESS live-smoke=SUCCESS`) over a commit **nobody had
  updated** — the repair went to the worktree's local branch `fix/storage-offload-detector`
  while the PR's head was `fix/storage-offload-detector-413` (renamed when the closure checker
  refused the first PR), so `git push origin HEAD` wrote to the wrong branch. Every LOCAL check
  said "up to date": `git rev-list --count HEAD..origin/master` was `0` and a dry-run merge was
  clean. The divergence was one `gh pr view` away and nothing made it.

The queue alarm (#252) covers a stuck **job**. Nothing covered a PR that runs **nothing**.

## What Changes

- **`scripts/pr_health.py`** — the decision, as a pure `findings()` plus `gh` reads: for every
  OPEN, non-draft PR, flag **`CONFLICTING`/`DIRTY`** and **no check runs on the head commit**,
  keeping the two reasons apart (a conflict cannot run anything; no runs without a conflict is a
  pipeline that never started). Prints the head branch, names the fix — `make worktree-resume`
  → merge the base → **`git push origin HEAD:refs/heads/<PR head>`** — and, with `--comment`,
  leaves ONE marker-deduplicated note per affected PR. Exit 1 when a PR is silent, 2 when `gh`
  fails.
- **`make pr-health`** (`REPO=` `COMMENT=1`) over the host recipe `_pr-health` — `gh` lives on
  the runner.
- **`pr-health.yml`** — twice an hour (`23,53`, off the hour), `guard` first with the schedule
  bypass, then `sweep` (`needs: guard`), commented with the **default** token
  (`pull-requests: write`, rule 6b). Registered in `BOT_GUARDS` (rule 6j) and in the #231
  coverage map (`tests/test_pr_health.py`).
- **`tests/test_pr_health.py`** (25 checks) drives the REAL script against a stub `gh`: a
  conflicting PR, a healthy one, a PR whose pipeline never started, drafts left alone, the
  comment's content and dedup, the pure decision, a `gh` failure, and the wiring.
- **`ARCHITECTURE.md`**: the target row, the `sweep` job row and its own section (rule 6h).

Verified RED against the pre-change tree (the module does not exist → the guard fails loudly)
and GREEN after (`PASSED 25 | FAILED 0`).

## Impact

`scripts/pr_health.py` (new), `Makefile` (two recipes), `.github/workflows/pr-health.yml` (new
pipeline), `tests/test_pr_health.py` (new), `tests/test_workflows.py` (`BOT_GUARDS` +
`DISPATCH_ONLY_COVERAGE`), `ARCHITECTURE.md`, this OpenSpec change and the regenerated
`OPENSPEC.md`.

## Not covered

- **Auto-repairing a silent PR.** Merging the base into someone's branch and pushing is a write
  the sweep must not make on its own; it flags and says exactly what to run.
- **Detecting a mismatched local branch from CI.** A runner cannot see the author's worktrees;
  the comment names the push shape instead, which is what the measured failure needed.
