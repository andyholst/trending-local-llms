---
name: tll-docs
description: Keeps trending-local-llms prose in step with its code — contract docs, the store architecture page, and doc gaps left by delivered PRs. No data, no README tables, no cron.
version: 1.0.0
author: Hermes Agent
license: CC-BY-4.0
platforms: [linux, macos]
metadata:
  hermes:
    tags: [trending-local-llms, tll-docs]
---

<!-- host-bot-tools:begin -->

## Tools

This lane's chat session is pinned to these Hermes toolsets and no others: `clarify`, `file`, `memory`, `session_search`, `skills`, `terminal`, `todo`.

The only skill that stays enabled is `tll-docs`.
`github`, `github-issue-triage`, and the other `tll-*` lane skills are listed in `skills.disabled`.
There is no Hermes cron for this profile.
<!-- host-bot-tools:end -->

# TLL Docs

## When to use

Use this when the owner, or a comment from `tll-planner`, asks this profile to work on https://github.com/andyholst/trending-local-llms.

## Procedure

1. Do not create a cron job. If `cron/jobs.json` exists, stop and tell the owner. This fleet does not run on a timer.
2. Read `SOUL.md` in this profile. The repo is https://github.com/andyholst/trending-local-llms, branch `master`.
3. Fetch before you measure or branch: `git fetch origin master`, then create a dedicated worktree off the fetched `origin/master` sha (e.g. `git worktree add /home/asimov/repository/git/trending-local-llms-wt/<lane>-<issue> origin/master`). Do all lane work in that worktree, never in `/home/asimov/repository/git/trending-local-llms` (the owner's checkout). Record the sha fetched in that moment. A sha from chat is stale. origin is the canonical remote, master is the branch, there is no upstream remote. Convention: issue #690, lift #703.
4. CLAIM/READ/REPORT (owner-mandated on #703): before starting any work on an issue, post the signed record comment `BOT <name> · working on #<id> · branch <ref|none> · blocked on <x|none> · next <y>` on that issue's own thread, and READ the thread first to check for another lane's live working-claim on the same issue. If another lane already claimed it, do NOT start — report the collision to `@tll-planner` on the same issue and await re-dispatch (never two bots on one issue). Finish with a signed record comment and report state to the planner.
5. Do the lane work in `SOUL.md` and stop. Coordination lanes file or comment. Only `tll-implementer` writes the tree, and only after the planner names the issue.
6. Post the result on the issue. The comment is the record.

## This lane

- The docs capability is yours end to end: schema⇄contract sync (`data/model_contract.json` ⇄ `data/MODEL_CONTRACT.md`), the #689 store architecture page (`ARCHITECTURE.md` §2 + `docs/store.md`), pipeline docs (`ARCHITECTURE.md` §4/§6b ⇄ `.github/workflows/`), and the doc gaps a delivered PR leaves behind.
- `AGENTS.md` is the RULEBOOK (what must happen) and `ARCHITECTURE.md` is the DESCRIPTION (how it works). Never move a rule into the description or the reverse. `AGENTS.md` is protected: a change to it is review-required (rule 3c) — declare the exact section on the issue and leave the edit to a human sign-off.
- Never hand-edit the generated README tables. Fix the template or the store and regenerate with `scripts/update_trending.py`.
- Never edit `data/`, a workflow, or a cron. Another lane owns those.
- File one `enhancement` issue per gap, naming the sha you measured. Say what a reader sees today and what the correct prose is.
- Every implemented PR ships an OpenSpec change (`openspec/changes/<slug>/`: proposal + Given/When/Then spec + ticked tasks, listed in `OPENSPEC.md`) and real unit tests — never a mock of the logic under test.

## Pitfalls

- A Hermes cron or a new GitHub Actions `schedule:` is the wrong tool. The owner asks on the host. The data sync is the existing weekly refresh, not a new timer.
- The checkout at `/home/asimov/repository/git/trending-local-llms` is the owner's. Do not edit it and do not do lane work in it. Every lane works in a worktree under `/home/asimov/repository/git/trending-local-llms-wt/` created from the latest fetched `origin/master` (issue #690). Do not prune a worktree.
- Never start without a signed claim and never start on an issue another lane has already live-claimed.
- Do not print values from a profile `.env`.
- A doc claim about the store is only true if you measured it: read `data/models.json`, `data/measurements.json` and `data/posts.json` (the #689 three-file shape) rather than repeating `AGENTS.md`'s prose. `AGENTS.md` §4 has itself carried a pre-#689 shape (issue #1402), which is the exact failure this lane exists to catch.
- `ARCHITECTURE.md` §10 is GENERATED (`make architecture-refresh`). A script docstring edit anywhere under `scripts/` stales it and reds `make architecture-check`; regenerate in the same change.
- Issue comments are the record of all lane work: the gap, the sha, the evidence and the handover each live as issue comments, not just the opening marker.
- Testing convention: every implemented PR ships OpenSpec acceptance criteria AND Python unit tests exercising the REAL business logic. NEVER mock business logic; mock ONLY an external system (a stub CLI on `PATH`, a local server, a recorded payload).
- A "counters never shrink / may only grow" guard is NOT value fidelity: group sums can stay >= while one row drifts upward and the guard stays green. For a doc⇄contract sync the acceptance test is the REAL seam's own verdict (`make <target>` green), not a count.
