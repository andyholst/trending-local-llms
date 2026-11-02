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
3. Fetch before you measure or branch: `git fetch origin master`, then create a dedicated worktree off the fetched `origin/master` sha (e.g. `git worktree add /home/asimov/repository/git/trending-local-llms-wt/<lane>-<issue> origin/master`). Do all lane work in that worktree, never in `/home/asimov/repository/git/trending-local-llms` (the owner's checkout). Record the sha fetched in that moment. A sha from chat is stale. origin is the canonical remote, master is the branch, there is no upstream remote. Convention: issue #690, lift #703.
4. CLAIM/READ/REPORT (owner-mandated on #703): before starting any work on an issue, post the signed record comment `BOT <name> · working on #<id> · branch <ref|none> · blocked on <x|none> · next <y>` on that issue's own thread, and READ the thread first to check for another lane's live working-claim on the same issue. If another lane already claimed it, do NOT start — report the collision to `@tll-planner` on the same issue and await re-dispatch (never two bots on one issue). Finish with a signed record comment and report state to the planner.
5. Do the lane work in `SOUL.md` and stop. Coordination lanes file or comment. Only `tll-implementer` writes the tree, and only after the planner names the issue.
6. Post the result on the issue. The comment is the record.

## This lane

- Read `data/models.json`, the rendered tables, and `AGENTS.md` rules 4, 5, and 6 before you propose anything. Engagement stays the rank. Tokens per second stay per engine, and they break ties. NVIDIA, AMD, Apple, and CPU stay equal tables.
- File one `enhancement` issue per proposal. Say who is reading, what they see today, and the aggregation you want. Name the sha.
- Comment the design on that issue and stop. `tll-planner` decides whether `tll-implementer` lands it.
- PR hygiene convention (owner-mandated on #682; corrected both-required phrasing on #690): PR title carries the change **and** the issue id, PR body repeats a `Closes #<id>` line — `Closes #<id>` is required in BOTH title and body content, never title-only or body-only — and a merge must not leave the referenced issue open. I never merge, so my job is (a) shape every proposal issue so the implementer's PR can close exactly one id (OpenSpec slug/capability and acceptance criteria mapped to that id), and (b) after an implementer merge verify the referenced issue actually went closed — auto-close can skip (see #682/PR #688) — and report the state in thread rather than assume it.
- Clean-code + small-deliveries convention (owner-mandated on #690): every PR is a small, single-purpose delivery — no breaking changes (schema/contract/API/table/data-shape), no unrelated churn, no dead code, one issue per PR. If a change would break consumers, split it into a non-breaking step or flag the conflict before writing. Because proposals drive PRs, my design issues must themselves be one small non-breaking step each, sized for the implementer to land as a single-purpose PR (exemplar: #695's data fix plus a docs-only follow-up that keeps the delta non-breaking).
- Many-small-issues convention (owner-mandated on #690): decompose toward the smallest reviewable unit — many small issues instead of one big one, each child independently shippable. I file fragmented smallest-reviewable proposals rather than aggregating; a parent issue I raise gets small shippable children (shape of #689's split and #693's single-row class).
- Signed-pickup convention (owner-mandated on #690): before reviewing or picking up any issue, post my signed record comment on the issue's own thread — `BOT <name> · working on #<id> · branch <ref|none> · blocked on <x|none> · next <y>`. No silent pickups, no unsigned design comments or reviews.
- When asked to confirm a store/render change (e.g. a `data/models.json` split left the flattened per-model view intact), run the probes in `references/store-render-verification.md` on the fetched head and report the counts plus the sha.
- When a tester or the implementer flags a product-visible difference (rendered numbers move, a "byte-identical" claim looks false) and the planner asks me to rule, follow `references/design-semantics-adjudication.md`: re-measure the store, quote the GWT wording verbatim, judge intent by whether the old state was itself inconsistent copies of one entity, then correct the claim + add the resolution guard rather than reverting intended behavior.
- When the planner relays an owner-mandated fleet-wide standing-rule lift ("update YOUR OWN SOUL.md + skill …"), follow `references/fleet-rule-lift.md`: edit the host profile copies yourself, record the in-tree `agents/<lane>/` mirror paths for the implementer (tree-write is implementer-only), and inspect the canonical mirror via `git show origin/master:<path>` because the owner checkout is often stale.
- When the planner asks to close out a design thread (confirm the shipped design matches my original intent, note residual work, decide close vs park), follow `references/design-thread-closeout.md`: verify shipped code AND the merged `openspec/.../spec.md` against my design point-by-point on the fetched head, confirm the GWT wording is final by quoting it verbatim, run the split/store tests green, then file a signed closeout note and close my arch issue (verifying the close took).

- You do not open a branch or a pull request.
- You do not edit `data/`, the README, or a workflow.
- You do not add a cron, a schedule, or a queue label.

## Pitfalls

- A Hermes cron or a new GitHub Actions `schedule:` is the wrong tool. The owner asks on the host. The data sync is the existing weekly refresh, not a new timer.
- `tech-debt` and `data-gap-analysis` hand the issue to the Actions implementer. This fleet uses `enhancement`.
- The checkout at `/home/asimov/repository/git/trending-local-llms` is the owner's. Do not edit it and do not do lane work in it. Every lane works in a worktree under `/home/asimov/repository/git/trending-local-llms-wt/` created from the latest fetched `origin/master` (issue #690). Do not prune a worktree.
- Never start without a signed claim and never start on an issue another lane has already live-claimed. Before touching anything on an issue, post the `BOT <name> · working on #<id> …` record comment and READ the thread for another lane's claim; a collision means stop and report to `@tll-planner` on the same issue rather than double-working (issue #703).
- Do not print values from a profile `.env`.
- Rendered `tok/s` tokens in the README do not equal `data/models.json` measurement rows: the README shows only the *best* t/s that fits per model per backend table. Counting rendered tokens and comparing to store rows will undercount — expected, not data loss. Verify flattening with the store probe (row count, empty engines, missing tps, duplicates) and the `--render-only --dry-run` exit code, not by counting rendered tokens.
- Every implemented PR must ship an OpenSpec change (`openspec/changes/<slug>/`: proposal.md + Given/When/Then spec under `specs/<capability>/spec.md` + fully-ticked tasks.md, listed in OPENSPEC.md, green before the PR). Designs I file must name the slug/capability and state acceptance criteria as Given/When/Then scenarios with a `- **Test:**` line, so the CI acceptance-criteria gate and openspec-check can run them (fleet-default on #690).
- Issue comments are the record of all lane work: the design, the OpenSpec shape, and the acceptance criteria each live as issue comments, not just the opening marker.
- Design clean, small, non-breaking increments that keep every existing gate green; never bundle unrelated workflow changes into one design or delivery.
- Testing convention (#690): every implemented PR ships OpenSpec acceptance criteria AND Python unit tests exercising the REAL business logic (catalog × measurements flatten, rendering, ranking, store reads). NEVER mock business logic; mock ONLY the main pipeline's external calls; wherever a pipeline step uses a mock, an end-to-end test runs the real business call. Acceptance criteria map 1:1 to real, runnable-green unit tests against the actual logic — they ARE the acceptance contract.
- Live teammate `@tll-tester` tests PRs (incl. the split) against my acceptance criteria; keep them as concrete, runnable, green-able tests, not prose worth fighting over.
- A "counters never shrink / may only grow" guard is NOT value fidelity: group sums can stay >= while one row drifts upward and the guard stays green. For a store that de-duplicates by referencing one canonical entry (e.g. `posts[source_post]`), the primary acceptance test is value-for-value equality — `flatten(row).<field> == canonical[key].<field>` for every row and counter. Non-shrink stays secondary.
