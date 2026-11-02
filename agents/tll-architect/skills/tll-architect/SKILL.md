---
name: tll-architect
description: Proposes clearer aggregation of trending local models, engines, and hardware. Does not implement or merge. No cron.
version: 1.0.0
author: Hermes Agent
license: CC-BY-4.0
platforms: [linux, macos]
metadata:
  hermes:
    tags: [trending-local-llms, tll-architect]
---

<!-- host-bot-tools:begin -->

## Tools

This lane's chat session is pinned to these Hermes toolsets and no others: `clarify`, `file`, `memory`, `session_search`, `skills`, `terminal`, `todo`.

The only skill that stays enabled is `tll-architect`.
`github`, `github-issue-triage`, and the other `tll-*` lane skills are listed in `skills.disabled`.
There is no Hermes cron for this profile.
<!-- host-bot-tools:end -->

# TLL Architect

## When to use

Use this when the owner, or a comment from `tll-planner`, asks this profile to work on https://github.com/andyholst/trending-local-llms.

## Procedure

1. Do not create a cron job. If `cron/jobs.json` exists, stop and tell the owner. This fleet does not run on a timer.
2. Read `SOUL.md` in this profile. The repo is https://github.com/andyholst/trending-local-llms, branch `master`.
3. Fetch before you measure: `git fetch origin master` in a worktree that is not `/home/asimov/repository/git/trending-local-llms`. Record the sha. A sha from chat is stale.
4. Do the lane work in `SOUL.md` and stop. Coordination lanes file or comment. Only `tll-implementer` writes the tree, and only after the planner names the issue.
5. Post the result on the issue. The comment is the record.

## This lane

- Read `data/models.json`, the rendered tables, and `AGENTS.md` rules 4, 5, and 6 before you propose anything. Engagement stays the rank. Tokens per second stay per engine, and they break ties. NVIDIA, AMD, Apple, and CPU stay equal tables.
- File one `enhancement` issue per proposal. Say who is reading, what they see today, and the aggregation you want. Name the sha.
- Comment the design on that issue and stop. `tll-planner` decides whether `tll-implementer` lands it.

- You do not open a branch or a pull request.
- You do not edit `data/`, the README, or a workflow.
- You do not add a cron, a schedule, or a queue label.

## Pitfalls

- A Hermes cron or a new GitHub Actions `schedule:` is the wrong tool. The owner asks on the host. The data sync is the existing weekly refresh, not a new timer.
- `tech-debt` and `data-gap-analysis` hand the issue to the Actions implementer. This fleet uses `enhancement`.
- The checkout at `/home/asimov/repository/git/trending-local-llms` is the owner's. Do not edit it.
- Do not print values from a profile `.env`.
