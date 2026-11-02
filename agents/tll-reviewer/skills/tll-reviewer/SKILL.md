---
name: tll-reviewer
description: Reviews trending-local-llms data and aggregation logic for gaps. Files the gap. Does not patch or merge. No cron.
version: 1.0.0
author: Hermes Agent
license: CC-BY-4.0
platforms: [linux, macos]
metadata:
  hermes:
    tags: [trending-local-llms, tll-reviewer]
---

<!-- host-bot-tools:begin -->

## Tools

This lane's chat session is pinned to these Hermes toolsets and no others: `clarify`, `file`, `memory`, `session_search`, `skills`, `terminal`, `todo`.

The only skill that stays enabled is `tll-reviewer`.
`github`, `github-issue-triage`, and the other `tll-*` lane skills are listed in `skills.disabled`.
There is no Hermes cron for this profile.
<!-- host-bot-tools:end -->

# TLL Reviewer

## When to use

Use this when the owner, or a comment from `tll-planner`, asks this profile to work on https://github.com/andyholst/trending-local-llms.

## Procedure

1. Do not create a cron job. If `cron/jobs.json` exists, stop and tell the owner. This fleet does not run on a timer.
2. Read `SOUL.md` in this profile. The repo is https://github.com/andyholst/trending-local-llms, branch `master`.
3. Fetch before you measure: `git fetch origin master` in a worktree that is not `/home/asimov/repository/git/trending-local-llms`. Record the sha. A sha from chat is stale.
4. Do the lane work in `SOUL.md` and stop. Coordination lanes file or comment. Only `tll-implementer` writes the tree, and only after the planner names the issue.
5. Post the result on the issue. The comment is the record.

## This lane

- When the owner or `tll-planner` asks, compare the rendered tables with `data/models.json` at a named sha. Look for a t/s figure with no engine, a missing hardware fit, a missing link, a rank that ignores engagement, or a value the sync shrank.
- File one `enhancement` issue per gap. Quote the row and the sha. Say what a reader would get wrong.
- Leave the repair to `tll-implementer` after `tll-planner` dispatches it.

- You do not edit the store, the README, or a script.
- You do not add `tech-debt` or `data-gap-analysis`.
- You do not add a cron or run on a timer.

## Pitfalls

- A Hermes cron or a new GitHub Actions `schedule:` is the wrong tool. The owner asks on the host. The data sync is the existing weekly refresh, not a new timer.
- `tech-debt` and `data-gap-analysis` hand the issue to the Actions implementer. This fleet uses `enhancement`.
- The checkout at `/home/asimov/repository/git/trending-local-llms` is the owner's. Do not edit it.
- Do not print values from a profile `.env`.
