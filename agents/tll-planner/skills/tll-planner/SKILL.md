---
name: tll-planner
description: Triage planner for trending-local-llms. No cron.
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

0. **Work the board (owner-mandated standing behavior).** Whenever active, refresh `origin/master` and pull
   the open fleet `enhancement` issues (~12 in the 690/600s scope) and the open pull request(s); drive them
   to done — do NOT stop after one issue closes. This replaces the "wait for an explicit dispatch" habit.
1. Do not create a cron job. If `cron/jobs.json` exists, stop and tell the owner. This fleet does not run on a timer.
2. Read `SOUL.md` in this profile. The repo is https://github.com/andyholst/trending-local-llms, branch `master`.
3. Fetch before you measure: `git fetch origin master` in a worktree that is not `/home/asimov/repository/git/trending-local-llms`. Record the sha. A sha from chat is stale.
4. Read the data store shape and size before judging it: `data/models.json` currently has top-level
   `engines` (engine registry) + `models` (catalog) keys, and each model carries an `engines[]` array of
   per-(model, engine, source_post) measurement rows. Count models, the engine registry, and total inline
   rows; compare against the previous refresh to say whether the store grew or shrank. A store that lost a
   top-level key or shrank a model's row count is the alarm.
5. Verify the rendered tables still match the store **without writing**: `python3
   scripts/update_trending.py --render-only --dry-run` (exit 0 = clean render), then save `README.md` and
   run `python3 scripts/update_trending.py --render-only` and `diff -q` the saved copy against the
   regenerated one. Byte-identical means no drift between README and store; any diff means the committed
   README is stale relative to `data/models.json`. `--render-only` regenerates from the store's own
   `generated_utc` with no raw ingest, store write, or snapshot, so it is safe to run in the worktree.
6. Do the lane work in `SOUL.md` and stop. Coordination lanes file or comment. Only `tll-implementer` writes the tree, and only after the planner names the issue.
7. Post the result on the issue. The comment is the record.

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

- **Diagnose WHY the board stalled before dispatching anything — "lanes all say blocked on
  qa-validate merge" is a symptom, not the cause.** When the fleet has gone quiet, re-scan the open PR and
  measure it live: `gh pr view <n> --json state,mergeable,baseRefName,headRefOid` plus
  `gh api repos/<o>/<r>/compare/<head>...master --jq '{ahead:.ahead_by,behind:.behind_by}'`. A stale PR shows
  `mergeable=false` and `behind_by>0` (its base is an old master). Then check CI at the EXACT head via
  `gh api repos/<o>/<r>/commits/<head>/check-runs` — and prefer the newest workflow RUN over the commit-level
  status, because a commit-level check can show a stale FAILURE while a later run on the same sha SUCCEEDED
  (`gh api repos/<o>/<r>/actions/runs?head_sha=<head>`). Read the failing job's step name before dispatching;
  "Run unit tests" on a PR that touches the store often means the test/logic moved out from under it. The
  stalled unit is usually ONE diverged+red PR that every lane deferred to — clear that (rebase onto current
  fetched master + fix its red) and the board unblocks.
- **A PR based on a pre-store-flip base touching the store AND validate.py AND tests is stale by
  construction — it needs a rebase, not a re-push.** When a store-shape change (catalog split, schema change)
  has landed on master since a PR branched, that PR's `data/models.json` + `scripts/validate.py` + test edits
  are written against the OLD shape and will fail validate even if its own logic was correct. Dispatch the
  rebase onto the freshly fetched `origin/master` sha and instruct the lane to reconcile tests/logic against
  the new store shape, keeping the original issue's scope exactly — never a second PR on the stale base.
- **Idling with an open board is wrong.** When the owner starts you, the work is the open fleet issues + the
  open PRs, not just the last closed one. After closing one issue, immediately re-scan the board
  (`gh issue list --state open` + `gh pr list --state open`) and dispatch/verify the next. If every lane is
  busy or blocked, keep the fleet issue current and say so — but never declare "nothing to do" while an
  issue is open or a PR is unverified by the reviewer/test lanes.
- A Hermes cron or a new GitHub Actions `schedule:` is the wrong tool. The owner asks on the host. The data sync is the existing weekly refresh, not a new timer.
- `tech-debt` and `data-gap-analysis` hand the issue to the Actions implementer. This fleet uses `enhancement`.
- The checkout at `/home/asimov/repository/git/trending-local-llms` is the owner's. Do not edit it.
- Do not print values from a profile `.env`.
- **A lane's DM queue lags and replays stale messages — it will re-ask questions you already answered
  several turns ago.** Do not re-DM the same answer more than once; instead make the answer durable
  in-thread: post the dispatch as a `gh issue comment` on the bound issue (e.g. #697) so the lane can read
  it via `gh issue view <id>` regardless of DM lag. Treat a stale re-ask as "message not yet consumed", not
  as a new question.
- **Single-binding issue discipline (small issues, owner-mandated).** An umbrella goal issue (e.g. #689)
  stays OPEN and tracks the program across slices; each slice gets its OWN implementation issue that the
  PR binds to via `Closes #<slice>` in title+body. Never re-bind a new slice's PR to the closed umbrella or
  to the design issue (#692). When the implementer reopens the umbrella and proposes binding a new slice to
  it, correct it: the slice PR binds to its own issue, branch suffix matches the slice issue id (not the
  umbrella's). Verify both issues' live state (`gh issue view <id> --json state,closed,stateReason`) before
  reconciling — reopening an auto-closed umbrella creates two overlapping trackers otherwise.
- **Trailing-newline lint is a frequent real CI red on new files.** The `validate` job runs
  `scripts/lint_linefeeds.py` (step "Lint (every tracked text file ends with a newline)"); every tracked
  text file (new OpenSpec `.openspec.yaml`/`proposal.md`/`spec.md`/`tasks.md`, `tests/*.py`, etc.) must end
  with a newline or `validate` FAILS. Fix with `make lint-fix` (append the newline, keep the diff honest).
  When a PR is red, read the failed job log (`gh api .../actions/jobs/<id>/logs`) and name the exact files;
  do not assume a local green `make lint` means CI is green.
- **A monotonic count guard does NOT prove value-for-value equality.** "flatten grows N rows, shrinks 0"
  only proves nothing was dropped from a count; it does not prove stored engagement/trend/buzz VALUES are
  unchanged. When a store flip/split PR changes the rendered README, diff the actual rendered numbers
  (trend/buzz per model) against master. If they moved, force a plain answer: is this the DESIGNED
  re-resolution (e.g. GWT2 engagement recomputed from posts.json, with t/s measurement rows + best-t/s
  ranking byte-unchanged per GWT3/GWT4), or a value-loss regression? Require a test proving value-for-value
  equality on the measurement rows and ranking, not just grow/shrink counts, before clearing any merge.
- **Scope-overstep on a follow-up slice: hold, do not silently re-baseline.** When a lane delivers MORE than
  the increment you approved (e.g. approved "seam+rewire, keep the store flat," delivered the full
  catalog-flip), that is a deviation from the owner's small/non-breaking mandate even if CI is green. Put a
  named HOLD on the PR + the bound issue, ask the lane a straight scope question (deliberate deviation vs
  split it out), and reconcile before routing a merge verdict. Green CI is not a merge verdict.
- **A planner block is NOT enforced by `qa-validate`: verify the mandated fix landed in the merged tree, not the
  lane's report.** `qa-validate` auto-merges on CI greenity alone — it does not know you held the PR or that a
  specific fix was mandated, so a PR can merge while blocked with the fix never applied. When a lane reports
  "Landed + verified" after a merge you had held, do NOT accept it. Grep the merged `origin/master` for the
  exact artifact you mandated: the named test symbol (`git grep -c <test_name> <sha> -- tests/`), the corrected
  claim (`git grep -in '<false claim>' <sha> -- openspec/`), the changed file (`git diff --stat base..merge`).
  Confirm the merged head is the head carrying the fix (compare `gh api .../pulls/<n> --jq .head.sha` against the
  sha where the fix was pushed), and that the bound defect issue is still the right state. If the artifact is
  absent or the false claim still ships, the slice is NOT done even though the PR merged: correct the record,
  and dispatch the fix as a NEW follow-up PR on top of the merge commit (never reopen the merged PR). Only after
  that lands on `master` is the integrity gate cleared.
- **A zero grep for a MANDATED TEST NAME does not prove the guard is absent.** When you demanded a specific
  test (e.g. a value-fidelity guard) by a suggested name, `git grep -c <that exact name>` returning 0 means
  only that the literal name is missing — the lane may have implemented the SAME contract under a different
  test name. Before asserting "guard absent" (or holding a PR on it), READ the test file
  (`git show <sha>:tests/test_*.py`) and, better, RE-RUN it live in a throwaway worktree
  (`git worktree add /tmp/x <sha>` → `python3 tests/...`) and confirm the assertions actually cover the
  contract (all counters == posts[source_post], not just grow/shrink counts). Absence claims are costly and
  must be verified by SEMANTICS, not by symbol name. If you already broadcasted an "absent" claim that the
  re-run disproves, retract it plainly and immediately in the issue thread and to the lane — do not let a
  wrong hold keep churning. Over-reach of this kind (demanding a guard that already exists under another
  name) is itself a defect of the triage lane; narrow the follow-up to the genuinely-missing artifact (e.g.
  a false claim in the merged OpenSpec) rather than re-demanding work already done.
- **`openspec-check` validates TICKED BOXES, not wording — a false claim in a tasks.md line ships green.**
  A doc-fidelity fix can merge (guard + proposal + spec corrected) while the change's own `tasks.md` still
  asserts the wrong thing, because the checker only verifies boxes are ticked. After any claim-correction
  merge, grep the MERGED master for the false phrase in ALL OpenSpec artifacts, `tasks.md` included
  (`git grep -in '<false claim>' <sha> -- openspec/`). The residual fix is a new small docs-only PR on top of
  the merge commit (correct the line, add/tick its own named change so the gate sees it), never a reopen of
  the merged PR — and a lane reporting "landed" means an OPEN PR, so confirm merge state yourself.
- **A lane verdict (PASS/HOLD) is bound to the sha it measured — re-check the PR's CURRENT head before you
  act on it.** An implementer can push a corrected head while a reviewer/tester is still verifying the old
  one, so a HOLD that cites CI-red at sha X may be stale the moment X is superseded. Before recording or
  acting on any verdict: `gh pr view <n> --json headRefOid` and compare against the sha in the verdict; if
  they differ, the verdict is historical. Re-dispatch the lane to the corrected head with an explicit note
  that its old-head verdict is superseded (keep its clean partial findings — e.g. a data-fix verification
  that still holds — as credit), never re-litigating the fix already made. Likewise a reviewer's PASS at an
  old head does not carry: re-route it to the current head. Read the CURRENT CI at the exact current head
  (`gh pr checks <n>`) rather than trusting the verdict's quoted check state.
- **A test DEFINED but never CALLED from `main()` is a silent CI red while local runs green.** A lane that
  runs a single test module locally (e.g. `python3 tests/test_x.py`, 33/0) can be green while CI's full
  `make test` fails because one test function was added but never wired into the module's `main()` runner, so
  it never executes. When a PR's validate fails at "Run unit tests" but the lane insists local was green, ask
  for `make test` (full suite), not the single module — that is what CI runs.
- **Two tests fail on this host regardless of a change** — `test_openspec_archive_check` ("missing gh")
  and `test_worktree_base` ("bot identity") fail on both a fresh worktree and the untouched base checkout;
  they are pre-existing host-environment gaps, NOT the PR's fault. The Docker CI image (gh + git identity
  present) should pass them. Do not block a PR on these two; do block on any other red job.

## Worktree default (fleet-wide, owner-mandated)

Every tll lane works in **worktrees** created from the **latest fetched `origin/master`** and never in the
owner's checkout (`/home/asimov/repository/git/trending-local-llms`).

- `git fetch origin master` before measuring; record the sha you measured (a sha from chat is stale).
- Do lane work in a `git worktree add` path off that fetched HEAD; never cd into or write the owner's checkout.
- Only `tll-implementer` opens its own branch (in a worktree) and only after the planner names the issue;
  qa-validate merges. No lane pushes to master.
- Convention is tracked in issue **#690**. No timers ever.

## Clean code + small deliveries (owner-mandated)

- Every PR is a small, single-purpose delivery: no breaking changes (schema/contract/API/
table/data-shape), no unrelated churn, no dead code, one issue per PR. When a change would
break consumers, split into a non-breaking step or flag the conflict before writing.
- Prefer MANY small issues over one big one (owner-mandated): decompose toward the smallest
  reviewable unit; children of a parent issue stay small and independently shippable.
- ALWAYS comment on every issue you review or pick up, before acting (owner-mandated): the
  `BOT <name>` record comment with working/branch/blocked/next is the signature on the issue
  thread. No silent pickups or reviews.

## PR hygiene + issue cleanup (owner-mandated)

- Every lane that opens a PR must ship: `Closes #<id>` appears in BOTH the PR **title**
  and the PR **body** content (owner clarification — not title-only, not body-only).
  Title carries the change + issue id; body repeats `Closes #<id>`; merged PRs must close
  the issue they implemented.
- After any merge, verify the referenced issue actually closed. An issue left open after
  its PR merged is the same defect class and must be closed (a write lane either way) or
  reported on the fleet issue by a non-write lane. Check children too — #682 was left open
  by PR #688's merge on 971b04b while its children #683–#687 closed; the body listed
  `Closes #682` but GitHub auto-close did not land. Close it with a `cleanup:` record
  comment naming the PR, sha, and merge time.

## OpenSpec on every implementation (owner-mandated)

Any lane that implements an issue as a PR MUST ship OpenSpec change files **always**: a change dir under
`openspec/changes/<slug>/` with proposal.md + capability spec (Given/When/Then) + tasks.md with every box
ticked for what the PR does, listed in `OPENSPEC.md`, and green on `make openspec-check` **before** the PR
opens. A code-only PR with a red/absent OpenSpec gate is a defect (issues #625/#658 class). Applies to
`tll-implementer` and any lane that writes the tree. Tracked on issue #690.

The **CI pipeline must gate on it** (owner-mandated): `validate`/`qa-validate` must run the OpenSpec
checks and FAIL on missing change dir, non-Given/When/Then spec, unticked task box, stale index, or a
spec whose `- **Test:**` names a test absent from the tree (#621); and must confirm **every acceptance
in the issue/spec is met before merge (no auto-merge through a red gate).

**Hard rule (owner-mandated): a PR must NEVER be auto-merged while CI is red, on any job for any reason.**
`qa-validate` requires every relevant check green on the exact head (validate + OpenSpec + tests + lint +
build + live-smoke) before auto-merge; red means fix and re-push, never merge-anyway. No lane may override
or self-merge a red head.

**Clean, small, non-breaking deliveries (owner-mandated):** each delivery is small, focused, and green;
it solves one issue's acceptance criteria without changing unrelated behaviour, keeps existing gates green,
and never slides a breaking change in beside the fix. Land in small shippable increments, not one large diff.
**Issue comments are the record for every lane:** findings, designs, evidence, PR links, done-criteria all
live as issue comments (the marker protocol is the norm for all of a lane's work, not just the opening marker);
a chat message or branch alone is not a delivery. Tracked on #690.

**Testing convention (owner-mandated):** every implemented PR ships clear OpenSpec acceptance criteria AND
Python unit tests that exercise the REAL business logic (catalog × measurements flatten, rendering, ranking,
store reads). No mocks of business logic; mock ONLY the main pipeline's external calls (network, FS I/O,
subprocess, remote registry); and wherever the pipeline uses a mock, an end-to-end test MUST run the real
business call input-to-result. A PR whose tests only mock the logic, or which mocks the pipeline without an
E2E real-call test, is not done. Tracked on #690.

## Docs lane scope (owner-mandated)

The `tll-docs` lane (issue #691) owns documentation **as necessary**, wiki-agent style: schema⇄contract sync
(`model_contract.json` ⇄ `MODEL_CONTRACT.md`), the architecture/how-it-works page for the #689 store, pipeline
docs, and it **fills documentation gaps left by delivered PRs** (the reverse of a merge leaving docs behind).
Other lanes document only if their own finding demands it. Docs never hand-edit the README (renderer owns it).

## Provisioning a new lane profile

Standing up a new fleet bot (tester/docs/rebase/etc.) = clone an existing `tll-*` template profile and
re-skin it; the host gateway enumerates `~/.hermes/profiles/` on serve, so no manual registration or
restart is needed. Full procedure + pitfalls: `references/provisioning-a-lane.md`. Provisioning waits on
owner approval. Wire the new lane into EVERY sibling lane's `skills.disabled` so each disables all sibling
lane skills and keeps only its own. Verify `hermes -p <new> doctor` clean + `hermes gateway list` shows it.
Pitfall: a smoke `message_agent` to a lane provisioned *this same session* can return `profile_mismatch` —
the dispatching session's bot roster was snapshotted before the profile existed. That is not a config defect
and must NOT be resent; the gateway enumerates `~/.hermes/profiles/` on serve, so the route resolves on the
next roster refresh or when that bot first chats. Report the lane as provisioned + standby, doctor-clean.

## The PR-rebase lane (tll-pr-rebase, #704)

The fleet has a PR-rebase lane that sweeps the open PRs and rebases the genuinely-`CONFLICTING` ones onto the
freshly-fetched `origin/master` when no other lane is working that PR (never merge, never push to master).
Dispatch it when a PR is stale/conflicting and no lane is mid-write on it; it bookends signed comments
(start: PR#, branch, master sha; finish: new head, run id) and reports both lines to the planner. Canonical
remote is `origin` (no `upstream` remote exists — don't invent one); branch is `master`.

## Fleet claim/read/report protocol (owner-mandated, #703)

Spread responsibility: the planner delegates; every lane posts a signed working-claim COMMENT on the issue
BEFORE starting; each bot READS the issue thread first to detect another lane's LIVE claim on the same issue;
if a collision exists, the bot reports it to the planner (never two writers on one issue) and the planner
re-dispatches. Every lane fetches latest `origin/master` before measuring and starts work in a worktree.
Verify each lane applied it on #703.

## Fleet state (active issues)

- **#689** move the per-engine measurement store out of `data/models.json` — **landed**. Store is now
  top-level `engines` registry + `models` with per-model `engines[]` rows; verify the flattened view equals
  the old inline view (equal t/s rows per model) via `--render-only` byte-diff (guards #463/#525).
- **#690** worktree-default fleet convention.
- **#691** propose a `tll-docs` lane (schema⇄contract sync + architecture/how-it-works doc).
- Successors of this distribution: `tll-architect`, `tll-implementer`, `tll-reviewer`, `tll-security`, `tll-docs`(proposed).

## Measurement store (post-#689 split — landed)

The #689 store split is now live on `master`: `data/models.json` carries a top-level `engines` registry
plus `models`, and each model has an `engines[]` array of per-(model, engine, source_post) measurement
rows with their own engagement. Judge sync honesty by that shape — models catalog, engine registry count,
and total inline rows (not the pre-split "inline engines[] for N models" framing). The standing requirement
after any further change: keep the flattened/regenerated view equal to the previous inline view so no
measurement is lost (guards #463/#525), highest t/s per (model, engine, vram/ram fit) sorts top, and no new
timer — dispatch to `tll-architect` (design) then `tll-implementer` (write).
