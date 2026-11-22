# Proposal: pr-health-bot-ownership-1295

Issue: #1295
PR: #1296

## Why

AGENTS.md rule 6s makes the open-PR rebase sweep mandatory, and the monitor's CI-failure branch says to rebase a behind PR. The shipped sweep decides ownership from `BOT_PUSH_PREFIXES = ("ci/", "tech-debt-", "data-gap-", "issue-")`. The agent's real PRs are named `fix/…`, `feat/…` and `rule/…`, so `rebase_plan()` labels them `human-branch` and never rewrites them; the mirror case rewrites a human's `ci/…` branch. On 2026-11-22 with a green `origin/master` (`c189c38d`) `make pr-health` reported 26 open PRs and 25 silent, and nine agent-owned branches had to be rebased by hand.

## What Changes

- Add `is_bot_owned(pr)` in `scripts/pr_health.py`: GitHub `author.is_bot` is authoritative; the prefix list is only a fallback when the author field is absent.
- Request `author` in `gh pr list --json` / `gh pr view --json` in both `pr_health.py` and `auto_merge_rebase.py`, and use `is_bot_owned` in `rebase_plan()` and `classify()`.
- Add pure tests for bot-authored `fix/feat/rule` (rebasable), human-authored `ci/tech-debt-` (report-only), the fallback with no author data, and the unchanged conflict rule.
- Replace the false prefix invariant in AGENTS.md §6s with the author contract.

## Impact

No workflow wiring, image, data format or credential change. The ruled human/bot partition is preserved — only its DECISION input changes from a naming convention to GitHub's author flag. A conflicting branch is still never rewritten, and a human branch is still report-only.

## Not covered

- No manual rebases of the remaining silent PRs; those stay with their own fix loops.
- No change to when the sweep runs, to CI dispatch, or to merge/access boundaries.
