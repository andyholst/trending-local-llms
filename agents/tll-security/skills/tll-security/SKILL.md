---
name: tll-security
description: Watches trending-local-llms code and container images for vulnerabilities. Files findings. Does not patch or merge. No cron.
version: 1.0.0
author: Hermes Agent
license: CC-BY-4.0
platforms: [linux, macos]
metadata:
  hermes:
    tags: [trending-local-llms, tll-security]
---

<!-- host-bot-tools:begin -->

## Tools

This lane's chat session is pinned to these Hermes toolsets and no others: `clarify`, `file`, `memory`, `session_search`, `skills`, `terminal`, `todo`.

The only skill that stays enabled is `tll-security`.
`github`, `github-issue-triage`, and the other `tll-*` lane skills are listed in `skills.disabled`.
There is no Hermes cron for this profile.
<!-- host-bot-tools:end -->

# TLL Security

## When to use

Use this when the owner, or a comment from `tll-planner`, asks this profile to work on https://github.com/andyholst/trending-local-llms.

## Procedure

1. Do not create a cron job. If `cron/jobs.json` exists, stop and tell the owner. This fleet does not run on a timer.
2. Read `SOUL.md` in this profile. The repo is https://github.com/andyholst/trending-local-llms, branch `master`.
3. Fetch before you measure: `git fetch origin master` in a worktree that is not `/home/asimov/repository/git/trending-local-llms`. Record the sha. A sha from chat is stale.
4. Do the lane work in `SOUL.md` and stop. Coordination lanes file or comment. Only `tll-implementer` writes the tree, and only after the planner names the issue.
5. Post the result on the issue. The comment is the record.

## This lane

- When the owner or `tll-planner` asks, read the tree at a named sha. Look at workflows, scripts, Dockerfiles, the agent image tag, and the secret scan. A finding names the path, the sha, and what is exposed.
- File one `enhancement` issue per finding. Never put a secret value in the issue. Say which image tag or digest you read.
- A hold needs the exposure, the issue that tracks the fix, and the evidence that would clear it. You do not write the patch.

- You do not open a branch, push a fix, or weaken a gate to make a scan green.
- You do not add a cron or a new GitHub Actions schedule.
- You do not print credentials, tokens, or `.env` values.

## Pitfalls

- A Hermes cron or a new GitHub Actions `schedule:` is the wrong tool. The owner asks on the host. The data sync is the existing weekly refresh, not a new timer.
- `tech-debt` and `data-gap-analysis` hand the issue to the Actions implementer. This fleet uses `enhancement`.
- The checkout at `/home/asimov/repository/git/trending-local-llms` is the owner's. Do not edit it.
- Do not print values from a profile `.env`.
