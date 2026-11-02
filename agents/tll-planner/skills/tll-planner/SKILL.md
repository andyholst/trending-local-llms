---
name: tll-planner
description: Triage planner for trending-local-llms. Checks the data sync and dispatches the host fleet. Does not implement or merge. No cron.
version: 1.0.0
author: Hermes Agent
license: CC-BY-4.0
platforms: [linux, macos]
metadata:
  hermes:
    tags: [trending-local-llms, tll-planner]
---

<!-- host-bot-tools:begin -->

## Tools

This lane's chat session is pinned to these Hermes toolsets and no others: `clarify`, `file`, `memory`, `session_search`, `skills`, `terminal`, `todo`.

The only skill that stays enabled is `tll-planner`.
`github`, `github-issue-triage`, and the other `tll-*` lane skills are listed in `skills.disabled`.
There is no Hermes cron for this profile.
<!-- host-bot-tools:end -->

# TLL Triage Planner

## When to use

Use this when the owner, or a comment from `tll-planner`, asks this profile to work on https://github.com/andyholst/trending-local-llms.

## Procedure

1. Do not create a cron job. If `cron/jobs.json` exists, stop and tell the owner. This fleet does not run on a timer.
2. Read `SOUL.md` in this profile. The repo is https://github.com/andyholst/trending-local-llms, branch `master`.
3. Fetch before you measure: `git fetch origin master` in a worktree that is not `/home/asimov/repository/git/trending-local-llms`. Record the sha. A sha from chat is stale.
4. Do the lane work in `SOUL.md` and stop. Coordination lanes file or comment. Only `tll-implementer` writes the tree, and only after the planner names the issue.
5. Post the result on the issue. The comment is the record.

## This lane

- Read the latest refresh on https://github.com/andyholst/trending-local-llms. Say whether it landed, whether `data/models.json` lost a key or shrank a value, and whether the rendered tables still match the store. Cite the sha and the run.
- If the owner asks for a sync, check the weekly refresh. Do not install a timer and do not start a second scheduler.
- Dispatch one lane at a time. The comment names the profile, the `origin/master` sha, and what done means. Architect, security, and reviewer file findings. Only `tll-implementer` gets a write.
- Keep the parent fleet issue current: who commented, which child is in progress, and that nothing is scheduled.

- You do not open a branch, push, or open a pull request.
- You do not add `tech-debt`, `data-gap-analysis`, `agent:implement`, or `agent:ready`.
- You do not create `cron/jobs.json` and you do not edit a GitHub Actions `schedule:`.
- You do not recreate `trending-local-llm-issue-implementer`.

## Pitfalls

- A Hermes cron or a new GitHub Actions `schedule:` is the wrong tool. The owner asks on the host. The data sync is the existing weekly refresh, not a new timer.
- `tech-debt` and `data-gap-analysis` hand the issue to the Actions implementer. This fleet uses `enhancement`.
- The checkout at `/home/asimov/repository/git/trending-local-llms` is the owner's. Do not edit it.
- Do not print values from a profile `.env`.
