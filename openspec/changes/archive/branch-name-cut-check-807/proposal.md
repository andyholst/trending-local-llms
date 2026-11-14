# Proposal: branch-name-cut-check-807

Issue: #807
PR: #951

## Why

A branch that implements issue `#N` must be named so that `scripts/pr_closure.py`'s parser
resolves it to `#N` (rule 6e). Nothing checked that at the cut. Measured (PRs #805/#803, runs
43104841635 / 43104841639): descriptive branches like `tech-debt-801-…-933` — which the parser
reads as issue **#933** while implementing #801 — sailed through `make worktree-new`,
`make branch-adopt`, the commit and the push, and went red ONLY at the PR webhook, on BOTH
`closure` and `validate`. The repair was worse than the bug: renaming the branch CLOSES the PR
and GitHub cannot reopen it, so each became a brand-new PR after a full CI cycle.

The cut is the last point where the mistake is cheap. At the webhook it is the most expensive
point in the pipeline.

## What Changes

- **`scripts/worktree_base.py` gains `--issue`** (modes `new` and `adopt`): when a cut declares
  the issue it implements, the branch NAME is validated through `pr_closure.implemented_issue`
  — THE parser `make pr-closure` applies (rule 6d: imported, never re-spelled). A name resolving
  to a different issue, or to none, is REFUSED (exit 1) before a worktree, branch or commit
  exists. `--issue` on any other mode is a usage error (exit 2); `--issue 0` is refused.
- **`adopt` still ATTACHES an existing branch** without the name check: its name was validated
  when it was cut, and the #500 rescue path (re-runs, branches cut before this rule) must stay
  open.
- **Makefile**: `make worktree-new` / `make branch-adopt` forward `ISSUE=<n>` as `--issue`;
  without it, behaviour is unchanged (keeper/refresh/descriptive cuts stay legal).
- **`issue-bot.yml`'s commit step** cuts with `ISSUE="$ISSUE"`: the bot's own
  `ci/data-gap-<issue>-<slug>` shape always satisfies the parser, so this is a regression net —
  if the branch construction and the issue ever diverge, the run dies at the cut, not at the
  webhook.
- AGENTS.md §6n gains the rule; §8's guard row is extended.

## Impact

- Affected specs: `worktree-base` (cut-name validation), `bot-coordination` (the bot's declared cut)
- Affected code: `scripts/worktree_base.py`, `Makefile` (`worktree-new`, `branch-adopt`),
  `.github/workflows/issue-bot.yml`
- Affected tests: `tests/test_worktree_base.py` (9 new tests; goes RED on the pre-fix script —
  verified against `git show HEAD:scripts/worktree_base.py`)
- No data, contract, or README-template change; no existing behaviour removed (additive seam).

## Not covered

- Renaming an EXISTING mis-named branch (GitHub closes the PR on rename — out of scope; the
  guard is preventive).
- Keeper branches (`ci/keeper-<slug>[-<issue>]`) and refresh branches: they implement no issue
  and are cut without `ISSUE=`; their legality is unchanged and asserted by
  `tests/test_pr_closure.py`.
