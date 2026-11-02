---
name: tll-implementer
description: Lands one dispatched trending-local-llms fleet issue at a time. No cron. Does not merge by hand.
version: 1.0.0
author: Hermes Agent
license: CC-BY-4.0
platforms: [linux, macos]
metadata:
  hermes:
    tags: [trending-local-llms, tll-implementer]
---

<!-- host-bot-tools:begin -->

## Tools

This lane's chat session is pinned to these Hermes toolsets and no others: `clarify`, `file`, `memory`, `session_search`, `skills`, `terminal`, `todo`.

The only skill that stays enabled is `tll-implementer`.
`github`, `github-issue-triage`, and the other `tll-*` lane skills are listed in `skills.disabled`.
There is no Hermes cron for this profile.
<!-- host-bot-tools:end -->

# TLL Implementer

## When to use

Use this when the owner, or a comment from `tll-planner`, asks this profile to work on https://github.com/andyholst/trending-local-llms.

## Procedure

1. Do not create a cron job. If `cron/jobs.json` exists, stop and tell the owner. This fleet does not run on a timer.
2. Read `SOUL.md` in this profile. The repo is https://github.com/andyholst/trending-local-llms, branch `master`.
3. Fetch before you measure: `git fetch origin master` in a worktree that is not `/home/asimov/repository/git/trending-local-llms`. Record the sha. A sha from chat is stale.
4. Do the lane work in `SOUL.md` and stop. Coordination lanes file or comment. Only `tll-implementer` writes the tree, and only after the planner names the issue.
5. Post the result on the issue. The comment is the record.

## This lane

- Wait for a `tll-planner` comment that names this profile, the issue, and the `origin/master` sha. Fetch that sha and branch in a fresh worktree. Do not use the checkout at `/home/asimov/repository/git/trending-local-llms`.
- One issue, one branch, one pull request. The branch ends in `-<issue number>` so `scripts/pr_closure.py` binds it. The body has its own `Closes #<issue>` line and no second closing reference on that line.
- Commits are authored `Andy Holst <andy.holst@protonmail.com>`. Open the pull request ready for review. `qa-validate` merges it when `validate` and `live-smoke` are green. Read the state back and comment the head sha.
- Copy the lane soul and skill you were dispatched to version into `agents/<profile>/` so the repo matches the host profile.

- You do not start because an issue exists. You start because the planner dispatched it.
- You do not run `gh pr merge`, do not approve your own pull request, and do not push to `master`.
- You do not add a Hermes cron or a GitHub Actions schedule. You do not label the issue `tech-debt` or `data-gap-analysis`.
- You do not take a red-PR repair. That stays with `trending-local-llm-issue-implementer`.

## Pitfalls

- A Hermes cron or a new GitHub Actions `schedule:` is the wrong tool. The owner asks on the host. The data sync is the existing weekly refresh, not a new timer.
- `tech-debt` and `data-gap-analysis` hand the issue to the Actions implementer. This fleet uses `enhancement`.
- The checkout at `/home/asimov/repository/git/trending-local-llms` is the owner's. Do not edit it.
- Do not print values from a profile `.env`.
