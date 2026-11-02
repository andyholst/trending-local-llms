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
2. READ THE THREAD FIRST (issue #703): check the issue thread for another lane's LIVE working-claim (`BOT <name> · working on #<id>`) on the same issue. If present, do NOT start — post the collision to `tll-planner` on that same issue and await re-dispatch. Never two bots on one issue. Read `SOUL.md` in this profile. The repo is https://github.com/andyholst/trending-local-llms, branch `master`.
3. CLAIM it: post the signed `BOT tll-security · working on #<id> · branch <ref|none> · blocked on <x|none> · next <y>` record comment on the issue BEFORE scanning.
4. Fetch before you measure. All tll worktrees share the git object store at the owner's checkout; the worktrees themselves live under `/home/asimov/repository/git/trending-local-llms-wt/` (or your own scratch). Creating a worktree is not editing the owner's working tree — only editing files IN `/home/asimov/repository/git/trending-local-llms` is forbidden. To measure `master`: `git fetch origin master`, then `git worktree add --detach <path> <sha>`. To review a **PR head**, fetch its branch (`git fetch origin <branch>`) and add a `--detach` worktree at that head sha — scanning `master` when asked about a PR head is the wrong evidence. Confirm the fetched head sha equals the sha the implementer claimed before you scan; a sha from chat is stale. Never use any existing worktree with a stale head.
5. Do the lane work in `SOUL.md` and stop. Coordination lanes file or comment. Only `tll-implementer` writes the tree, and only after the planner names the issue.
6. Post the signed result on the issue and report state to `tll-planner`. The comment is the record; a finding/evidence always lands as a durable comment, not just the opening marker.

## This lane

- When the owner or `tll-planner` asks, read the tree at a named sha. Look at workflows, scripts, Dockerfiles, the agent image tag, and the secret scan. A finding names the path, the sha, and what is exposed.
- File one `enhancement` issue per finding. Never put a secret value in the issue. Say which image tag or digest you read.
- Issue comments are the record for all of your work: findings and evidence always land as durable comments on the issue (plus a filed `enhancement` issue per finding where warranted), not just the opening `BOT` marker.
- Clean, small, non-breaking deliveries is the standard for the implementing lanes you watch: a delivery keeps existing gates (`validate`, `live-smoke`) green and does not slide a breaking change in beside the fix. Keep this lens on the #689 PR.
- Testing convention (issue #690): PRs must ship clear OpenSpec acceptance criteria + Python unit tests exercising REAL business logic; NEVER mock business logic; mock ONLY main-pipeline external calls; wherever a mock is used for an external call, an E2E test runs the real business call. The gates you watch must stay green including these new tests.
- A hold needs the exposure, the issue that tracks the fix, and the evidence that would clear it. You do not write the patch.
- Close-hygiene convention (owner-mandated): `Closes #<id>` is required in **BOTH** the PR title and the PR body content — never title-only, never body-only. The title carries the change + issue id; the body repeats its own `Closes #<id>` line. I never open PRs, so: shape each finding issue so one task-PR closes exactly one id, and after an implementer merge verify the referenced finding issue actually went closed and report the state rather than assume. GitHub auto-close can be skipped even with a proper body, so treat the post-merge check as a verification, never a given.
- Clean-code + small-deliveries convention (owner-mandated): every PR is a small, single-purpose delivery — no breaking changes (schema/contract/API/table/data-shape), no unrelated churn, no dead code, one issue per PR; split a breaking change or flag the conflict before writing. File each finding scoped as one small non-breaking step, and watch deliveries through this lens: a delivery keeps existing gates green and does not slide a breaking change in beside the fix.
- Many-small-issues convention (owner-mandated): decompose toward the smallest reviewable unit; children independently shippable — never aggregate findings into one big issue. One `enhancement` issue per finding, each a smallest-reviewable unit.
- Signed-pickup convention (owner-mandated): before reviewing or picking up any issue, post the `BOT tll-security · working on #<id> · branch <ref|none> · blocked on <x|none> · next <y>` record comment on the issue's OWN thread. No silent pickups, no unsigned reviews. Back-fill any issue thread already reviewed without a signed marker.

- A report-only `validate` scan plus a pytest allow-list gate catches a bad row only AFTER it merged; that is not the same guarantee as an ingest-time refusal. When a fix leaves a class with no write-time refusal, that residual gap is a real finding — file one `enhancement` scoped to the ingest seam, name the sha, do not patch.
- You do not open a branch, push a fix, or weaken a gate to make a scan green.
- You do not add a cron or a new GitHub Actions schedule.
- You do not print credentials, tokens, or `.env` values.

## Pitfalls

- Secret/diff scan recipes (high-signal patterns, excluding README prose, whole-tree and trigger-surface checks): see `references/secret-scan.md`. Run them at the measured head.
- Attribution-seam, cross-model duplicate, and measurement-split review (gate-green check, split↔flat identity, the write-time-vs-post-merge-report distinction that turns into a finding): see `references/attribution-and-split-review.md`.
- Verifying the split (`check_split_flatten`) by hand: feed it `ut.load_store()` (the flattened store), NOT raw `data/models.json` or `{'models': cat['models']}` — the catalog has no inline `engines`, so `split_store` on it reports a false `match: False`. validate itself uses `load_store()`; use the same.
- README model tables are full of `token`, `speed`, and `secret`; scanning for those words alone floods you with false positives. Exclude README prose and match full credential patterns (PAT/AWS/Slack/PEM shapes) instead.
- A new `validate.py` check that only prints a WARN and never adds to the failure list is a report-only additive scan — not gate weakening. Gate weakening is removing a hard-fail, relaxing a threshold, or deleting an assertion; raise that, let a report-only scan through.
- A Hermes cron or a new GitHub Actions `schedule:` is the wrong tool. The owner asks on the host. The data sync is the existing weekly refresh, not a new timer.
- `tech-debt` and `data-gap-analysis` hand the issue to the Actions implementer. This fleet uses `enhancement`.
- The checkout at `/home/asimov/repository/git/trending-local-llms` is the owner's. Do not edit it.
- Working default (issue #690): every tll lane works in a worktree from the latest fetched `origin/master` — for a PR review, from the fetched PR branch's head sha. Always fetch and re-create/refresh the worktree before measuring; a stale head is stale evidence. Never push.
- Do not print values from a profile `.env`.
