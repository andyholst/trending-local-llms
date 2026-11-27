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
No blind LLM dispatch cron exists for this profile. The sole exception is the owner-authorized,
marker-gated watcher pair (no-LLM watchdog + monitor-gated agent) — see `references/watcher-trigger.md`.
<!-- host-bot-tools:end -->

# TLL Triage Planner

## When to use

Use this when the owner, or a comment from `tll-planner`, asks this profile to work on https://github.com/andyholst/trending-local-llms.

## Procedure

0. **Work the board (owner-mandated standing behavior).** Whenever active, refresh `origin/master` and pull
   the open fleet `enhancement` issues (~12 in the 690/600s scope) and the open pull request(s); drive them
   to done — do NOT stop after one issue closes. This replaces the "wait for an explicit dispatch" habit.
   This owner's standing style this cycle: delegate without waiting for a human go-ahead, open every PR
   ready (never draft), and keep the board moving — dispatch more lanes whose target files differ, and
   keep the CI of red failures under monitoring (re-scan the open PRs, re-read the threads, dispatch the
   reviewer/tester lanes for verdicts, hold/re-route as needed). Every dispatch, status, verdict and
   closer is posted on the issue's OWN thread in the signed `BOT <name> · …` record; the chat carries only
   the conclusion.
1. Do not create a blind cron that starts lane work, and do not add or edit an Actions `schedule:`; the
   owner starts the fleet. The only permitted cron is the owner-authorized, marker-gated watcher pair
   documented in `references/watcher-trigger.md` — never create it without explicit authorization and
   never register a second pair on a host that already has one.
2. Read `SOUL.md` in this profile. The repo is https://github.com/andyholst/trending-local-llms, branch `master`.
3. Fetch before you measure: `git fetch origin master` in a worktree that is not `/home/asimov/repository/git/trending-local-llms`. Record the sha. A sha from chat is stale. **Never extend a short sha quoted in a comment into a full one by guessing** — `git rev-parse origin/master` and `gh pr view <n> --json headRefOid` are the only sources for a 40-char sha in a dispatch; a fabricated ref sends the lane to a nonexistent commit and wastes its whole run.
4. Read the data store shape and size before judging it: `data/models.json` currently has top-level
   `engines` (engine registry) + `models` (catalog) keys. MEASURED 2026-11-23 at `f2b3db89`: `models` is a
   LIST and a model row has NO `engines[]` — its per-(model, engine, source_post) measurement rows live in
   `engagement.seen_posts[]`, each with `url`, `date`, `engine`, `tps`, `hardware`, `quant`, `likes`,
   `comments`, `reshares`, `views`. Count models, the engine registry, and total `seen_posts` rows;
   compare against the previous refresh to say whether the store grew or shrank. A store that lost a
   top-level key or shrank a model's seen-posts count is the alarm.
5. Report whether the rendered tables still match the store WITHOUT executing anything locally: read the
   verdict from the newest push-to-master `qa-validate` run (`gh run view <id> --json jobs`), whose
   `readme`/`validate` stage re-renders and fails on drift. The standing owner directive is that NO
   product command, renderer, validator or `make` target runs on the host — even a `--render-only --dry-run`
   probe is a local execution. Read blobs with `git show <sha>:<path>` when byte detail is needed; full
   method in `references/data-sync-readback.md`.
6. Do the lane work in `SOUL.md` and stop. Coordination lanes file or comment. Only `tll-implementer` writes the tree, and only after the planner names the issue.
7. Post the result on the issue. The comment is the record.

### Starting a lane (owner directive 2026-11-23)

The owner directed on 2026-11-23 that this lane has **full authority to orchestrate and delegate**: you
START the other lanes yourself instead of waiting for the owner on the host, and you run the commands
needed to move the board.

- Start a lane with `env -u HERMES_HOME -u HERMES_SESSION_PROFILE hermes -p <lane> chat
  --query-file <file> --oneshot`, launched via `terminal(background=true)` and monitored with
  `process_manage`. The query file carries the signed dispatch: the lane profile, the issue, the fetched
  `origin/master` sha, what done means, and the handover target.
- Delegation is still by a signed dispatch COMMENT on the issue thread — post the dispatch comment first,
  then start the lane against that issue.
- **A dispatch's `done` is push-and-verify, never a local gate.** The query file tells the lane: make the
  change in its worktree, run only the fast offline checks (`python3 scripts/pr_body.py --check-body-file
  <f> --branch <b>`, `make lint`, the targeted unit module), PUSH, then confirm CI registered on the new
  SHA (`gh pr checks <n>`, `gh run view <id> --json jobs`) before reporting. Do NOT ask a lane to prove
  the whole containerised suite green on the host before it pushes — full `make validate`, the whole
  `make test` and `make live-smoke` are CI-ONLY (they run on `qa-validate`; locally 15–30 min each, and N
  lanes running them at once contend for one container VM). Owner directive 2026-11-23, tracked on #1423.
- The planner still NEVER writes the tree and NEVER merges. Starting a lane is dispatch, not
  implementation; only `tll-implementer` writes, and `qa-validate` merges green.
- No cron and no Actions schedule: the directive changes who starts the lanes, not the cadence. Blind LLM dispatch is never scheduled; the owner-authorized, marker-gated watcher pair is the sole exception (see `references/watcher-trigger.md`).
- **Pitfalls.** Pass `--yolo --accept-hooks`, or the lane hits `approvals.single_query_mode: deny` on
  `git push --force`. After a lane run, check the owner's checkout with `git status` — a lane's shell cwd
  is not automatically its worktree. A lane runs 30–70 min; monitor it with `process_manage` and do not
  assume it finished.
- **A pushed branch with NO PR is a DEAD lane — dispatch a RESUME, never a second implementation.**
  Measured #1467: the implementer's complete commit `02ec523f` reached `origin` at 03:37Z, the lane
  process was gone by the next watch cycle, and no PR existed. Before re-dispatching check THREE things:
  `ps` for a live `hermes -p tll-* chat`, `gh pr list --state all --head <branch>`, and whether the pushed
  commit already carries the full delivery (OpenSpec change dir bound to the issue, tests, ARCHITECTURE
  rows, findings). If it does, the dispatch is a bounded RESUME — open the PR from the EXISTING head, run
  fast offline checks, fix loop, push — and must forbid cutting a new branch or rewording the commit. Run
  `make dispatch-check ISSUE=<n>` first (it reads live state) and honor the §7b race guard (post the
  dispatch, wait ~80 s, re-read the thread, start only if your comment is still newest).
- **A lane that stops on a measured blocker gets a bounded RESUME, not a second implementation.** When a
  lane posts a signed blocker with options, answer with ONE explicit ruling naming the chosen option,
  the base sha, the exact preconditions (remote ref, gates already green) and the single next delivery;
  forbid re-doing work already verified. Continue the SAME lane session with the resume command printed
  at exit: `hermes --resume <session-id> -p <lane> chat --query-file <resume-file> --oneshot --yolo
  --accept-hooks`. The resume file is a dispatch prompt (name it `resume-*`), not the ruling comment.
  A master-move merge-tree red is a race, so authorise ONE bounded rebase with the lease pinned to the
  current head; if master moves again the lane must report the race, not loop. Read the FULL verdict body
  before writing the resume: a reviewer can mark a HOLD for a race while separately naming a shipped
  defect (a spec pointing at absent tests, a false body claim). A rebase-only resume clears the HOLD and
  leaves the real defect in the merged tree — put every named defect in the SAME bounded dispatch,
  labelled primary vs secondary, and forbid re-litigating work already verified.
- **A DIRTY, far-behind PR gets a bounded RE-CUT, not a second implementation and not a blind rebase.**
  Measure the delta first (`git log --oneline origin/<branch> --not origin/master`, and compare the head
  with master via `gh api repos/<o>/<r>/compare/<head>...master --jq '{ahead:.ahead_by,behind:.behind_by}'`).
  Instruct the lane to keep ONLY the wanted additive delta (an evidence record, its OpenSpec change and
  findings, the regenerated index), restore every conflicting file to the fetched master's LANDED shape
  verbatim, drop a guard ONLY when master already carries THAT SAME guard, and force-push to the EXISTING
  branch with `--force-with-lease` pinned to the measured stale head — STOP if the ref moved. **Before
  pushing, resolve every `- **Test:**` line in the PR's bound OpenSpec spec against the new head**: a
  narrow re-cut silently drops the issue's OWN test functions along with the unwanted churn, and an
  ARCHIVED change is exempt from the test-line gate, so CI stays green while the spec names tests that
  no longer exist. Restore those tests in the same head. Then verify the new diff is additive
  (`gh pr diff --name-only`) and that CI registered with real jobs at the new head before routing a
  reviewer. This is the resume shape for a PR that exists but is stale/conflicting.

## This lane

- Read the latest refresh on https://github.com/andyholst/trending-local-llms. Say whether it landed, whether `data/models.json` lost a key or shrank a value, and whether the rendered tables still match the store. Cite the sha and the run.
- If the owner asks for a sync, check the weekly refresh. Do not install a timer and do not start a second scheduler.
- Dispatch lanes in PARALLEL whenever their target files differ — the owner requires continuous work,
  not a serial queue, and worktrees isolate the trees (#1423/#1424 removed the local-VM reason for a
  serial cap). **A running lane never blocks the next dispatch:** fill every free implementer slot up
  to the ceiling with a distinct open issue, and dispatch reviewers/designers on open PRs and filed
  gaps in the same pass. Lanes already running is not a reason to end the turn — idle slots are lost
  capacity and the board, not the chat, is the work surface. The comment still names the profile, the `origin/master` sha, what done means, and the
  handover target. Serialise ONLY shared files via `make dispatch-check ISSUE=<n> MACHINE=<user@host>
  CLAIMS="p1 p2"` (#1458 path overlap, #1569 cross-host claims): `agents/*/skills/*/SKILL.md`, `OPENSPEC.md`
  and generated artifacts. Architect, security, and reviewer file findings; only `tll-implementer` gets a
  write. Never answer a full board with a status report while a distinct issue or PR is movable.
  When no unclaimed actionable issue exists but one gate defect has produced several measured red
  runs, FILE ONE evidence-backed issue naming those runs and dispatch design/implementer lanes against
  it — an empty actionable queue is a signal to create the next small issue, not to idle a free slot.
- Keep the board current on each issue's OWN thread (the parent fleet issue #682 is closed): who commented, which lane is in progress, and that nothing is scheduled.

### Parallel implementer dispatch (owner directive, issue #1767)

The owner directed on 2026-11-26 that the board is not drained one issue at a time:
dispatch up to 3 implementer lanes CONCURRENTLY against DISTINCT open issues whenever
their target files differ. Serialise only a genuine shared-file collision through
`make dispatch-check ISSUE=<n> MACHINE=<user@host> CLAIMS="p1 p2"`; never rely on
recollection of the board. Every concurrent lane is separately accountable:

- one query file per lane (`dispatch-tll-implementer-<issue>.txt`) carrying the signed
  dispatch — profile, issue, fetched `origin/master` sha, done criteria, handover;
- one signed issue claim per lane (the twice-claim race guard on that issue's OWN thread)
  before the lane starts; two lanes never hold one issue;
- one worktree per lane off the fetched `origin/master` sha, never the owner's checkout;
- one lease-checked branch per lane: the branch ends in `-<issue>` and the push pins
  `--force-with-lease` to the freshly fetched remote ref — STOP if the ref moved;
- one board-visible bookend per lane: the signed `BOT tll-planner · dispatch #<id>`
  start and the signed `BOT tll-implementer · done #<id> · handover <...>` finish,
  both on the issue's OWN thread — a chat message or a branch alone is not a bookend.

Do not dispatch onto a tech-debt issue or a protected-rulebook issue (`AGENTS.md`
§7b/§8 or an `agents/*/SOUL.md` edit under rule 3c) without explicit owner sign-off
on that issue thread; a reviewer's process acceptance is not write approval. This
lane still writes no tree, has no merge and no push to master: a green-head merge
belongs to the qa-validate gate alone.

- You do not open a branch, push, or open a pull request.
- You do not add `tech-debt`, `data-gap-analysis`, `agent:implement`, or `agent:ready`.
- You do not create `cron/jobs.json` and you do not edit a GitHub Actions `schedule:`.
- You do not recreate `trending-local-llm-issue-implementer`.

## User style (owner correction)

The owner's messages are terse and demand results: implement the issue, create the PR, deliver it. The planner's chat output must be:

- **Short and result-first:** the conclusion (delivered, what it changed, the one open item and its URL) before any background — the issue thread is the record, the chat carries the conclusion. No process narration (dispatch waits, status loops, lane detail).
- **While lanes are in flight, the chat gets one line, not a status log.** Name what is running and the single owner-gated item, then end the turn and resume on lane-completion notifications — but ONLY after every movable issue/PR already has a lane. The issue thread already holds every step; narrating waits in chat reads as an answer to a question nobody asked.
- **Links only, one line each:** PR URL, gate run URL, issue URL.
- **Never re-report a closed issue** without re-reading the thread — state from chat is stale; a claim is valid only against the current head.
- **Everything a lane comments appears on the issue's own thread** in the signed `BOT <name> · …` record format — dispatch, status, verdict, closer. A chat message is never a delivery.

## PR gate diagnosis (pr-closure red)

The fleet merge gate is `pr-closure`. This cycle it refused a branch twice for the same class of defect: the gate binds every `#<id>` in the PR title/body as a closing reference, so prose mentioning another issue (`their own PRs closed #1747`) is parsed as closing that issue and rejects the branch; and the title must carry the closing keyword for THIS issue unmasked, or the branch cannot bind it. Diagnose and fix with this recipe:

1. **Reproduce first.** Run the live body preflight `make pr-message-check PR=<n>` before posting any PR handover, and reproduce the closure gate with its SUPPORTED inputs: `make pr-closure PR_EVENT=<event json>` or `make pr-closure BRANCH=<head ref> BODY_FILE=<body file>`. `make pr-closure PR=<n>` is NOT a supported invocation and exits 2. Read the job log for the failing step. A PR with **no checks reported** on the branch is never green (a never-started head) — name the run URL and head sha before re-pushing.
2. **List the bindings.** Read the PR title and body; every `#<id>` that is NOT the PR's own `Closes #<n>` is a candidate defect.
3. **Reword the mis-bound prose.** A cross-reference like `#1747` becomes inline code (`` `#1747` ``) — the gate strips inline-code spans, so masking hides the reference from its parser while keeping the record readable. Never remove it; never rewrite the record's meaning.
4. **Unmask the issue's keyword in BOTH title and body.** `Closes #<id>` must appear in the title AND in the body content — title-only and body-only do not close the issue on merge.
5. **Re-run the gate to green** on the final head, then re-trigger the full `validate`/`live-smoke` CI on a file change. File-filtered workflows do NOT fire on metadata-only commits; the pr-closure workflow fires. If `validate` stays red after the gate is green, fix the CODE (read the job log), not the trigger — do not add workflow edits to fix a CI-trigger artifact.

### Rebinding an existing PR to a different issue

Before telling a lane to re-bind an open PR, measure three seams against the live tree and rule from the results; a body-only `Closes` edit is never enough:

- `python3 scripts/pr_closure.py --branch <branch> --body-file <body>` and `python3 scripts/pr_body.py --check-body-file <body> --branch <branch>` derive the implemented issue from the branch's trailing `-<number>`, so a body that binds a different issue is refused. Do not instruct a dual bind or a misleading branch name to dodge it.
- `python3 scripts/openspec_archive_check.py --pr <n>` requires a change whose `Issue:` line names the NEW issue; an existing change bound to the old issue does not satisfy it.
- `make findings-check-for-pr` resolves the analysis by the issue the PR closes, so the branch also needs `findings/<new-issue>.md`; an analysis named after the old issue does not count.

GitHub's branch-rename API moves the ref but does NOT re-point an open PR's head ref, and deleting the old head closes the PR. When the branch name must encode the new issue, rule the bounded supersession: push the prepared head to a fresh `-<new-issue>` branch, open one READY PR with `Closes #<new>` in title and body, correct the OpenSpec `PR:` line to the new PR number, add the new findings file, then close the old PR unmerged with a signed supersession comment. Mask the old reference as inline code so it is not a second closing binding. Never assume a REST/GraphQL mutation can change a PR head ref.

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
  issue is open or a PR is unverified by the reviewer/test lanes. **When every lane is CI-bound, do NOT post
  another status report on the same wait — that is idling in prose.** Pick the next movable thing (a stale or
  conflicting PR, a filed gap, an unclaimed issue, a host-gate divergence) and move it; repeat the wait only
  when the state actually changed. Tracker cleanup needs NO lane: close issues left open after their fix
  merged and superseded duplicate PRs yourself with signed evidence while the implementers wait on CI.
- A Hermes cron or a new GitHub Actions `schedule:` is the wrong tool. The owner asks on the host. The data sync is the existing weekly refresh, not a new timer.
- `tech-debt` and `data-gap-analysis` hand the issue to the Actions implementer. This fleet uses `enhancement`.
- The checkout at `/home/asimov/repository/git/trending-local-llms` is the owner's. Do not edit it.
- **Verify a landed change against `origin/master`, never the owner's checkout.** The owner's checkout can
  sit several commits behind with uncommitted edits, so a probe run there silently tests STALE code — a fix
  that already merged can look absent and you will file a false gap. Probe in a throwaway detached worktree at
  the fetched sha (`git worktree add --detach <scratch>/verify <sha>` → run the check / the module's tests →
  `git worktree remove --force <path>`), and always name the sha you measured. Compare
  `git rev-parse HEAD` against `origin/master` before trusting any local reproduction.
- Do not print values from a profile `.env`.
- **A lane's DM queue lags and replays stale messages — it will re-ask questions you already answered
  several turns ago.** Do not re-DM the same answer more than once; instead make the answer durable
  in-thread: post the dispatch as a `gh issue comment` on the bound issue (e.g. #697) so the lane can read
  it via `gh issue view <id>` regardless of DM lag.  Treat a stale re-ask as "message not yet consumed", not
  as a new question. Lane-completion notifications replay the same way: if the merge and cleanup were
  already verified from live state, re-measure the PR and issue once and post no duplicate bookend.
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
  that lands on `master` is the integrity gate cleared. The same applies to a HOLD on a duplicate PR:
  `qa-validate` merges on green alone and does not read the HOLD. Re-read `gh pr view --json
  state,mergedAt` after posting it; if the duplicate merged first, close the competing PR/issue with a
  signed supersession record, back off and kill any lane still working that branch, rather than
  continuing a review of a defect already resolved on master.
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
- **A `make test` red naming a guard that asserts an old literal shape is a guard-update task, not a
  runtime regression.** When a refactor moves values into a new variable or flag, first prove the effective
  runtime configuration is byte-identical (diff the resolved old and new values), then update the test in
  the SAME PR to resolve the new seam. Never revert the refactor or weaken the assertion into a skip. A
  reviewer HOLD for this class must name the exact assertion lines and the replacement seam.
- **A test DEFINED but never CALLED from `main()` is a silent CI red while local runs green.** A lane that
  runs a single test module locally (e.g. `python3 tests/test_x.py`, 33/0) can be green while CI's full
  `make test` fails because one test function was added but never wired into the module's `main()` runner, so
  it never executes. When a PR's validate fails at "Run unit tests" but the lane insists local was green, ask
  for `make test` (full suite), not the single module — that is what CI runs.
- **Two tests fail on this host regardless of a change** — `test_openspec_archive_check` ("missing gh")
  and `test_worktree_base` ("bot identity") fail on both a fresh worktree and the untouched base checkout;
  they are pre-existing host-environment gaps, NOT the PR's fault. The Docker CI image (gh + git identity
  present) should pass them. Do not block a PR on these two; do block on any other red job.
- **Bound lane concurrency — at most 3 `tll-implementer` lanes at once, and never dispatch to a closed
  issue or an already-merged PR.** Measured with 7 concurrent lanes: load average 7.08, the host VM at 348%
  CPU, runtimes of 66–128 min, including a 95-min lane (#1239) working an issue that was already CLOSED.
  Every head passes the containerised `make validate` in CI (#712), so N lanes do not finish N times
  faster — they contend for ONE container VM. Unbounded lanes do not finish faster: every head must pass
  the containerised gate, so N lanes contend for ONE host VM while each lane process idles at ~0% CPU in
  `sleep` polls — and a lane can burn an hour on an issue that is already CLOSED. The ceiling was calibrated when
  lanes pre-ran the containerised suite locally; push-and-verify (#1423/#1424) removed that CPU cost, so treat it as
  a safety bound, NOT a reason to idle — dispatch every movable lane whose target files differ, up to the
  ceiling. Enforce BOTH halves mechanically BEFORE spawning: `make dispatch-check ISSUE=<n> MACHINE=<user@host>
  CLAIMS="<paths>"` refuses a CLOSED issue or a bound PR that is already MERGED, prints `active_lanes=<n>/<ceiling>`
  and refuses above it, and refuses a path another ACTIVE lane claims (#1458) or a NEWER working-claim ANOTHER
  host holds (#1569). Do not rely on your own recollection of the board — a state or sha from chat is stale, and
  the guard reads live GitHub state (repo guard: issue #1416).
- **Protected instruction files cannot be written by a headless lane — declare them owed to the owner and
  do not route around it.** `agents/*/SOUL.md` and `AGENTS.md` §7b/§8 are rule-3c protected: the write is
  refused (`security.protected_instruction_files=true`) and a TIMED-OUT approval prompt is NOT consent. When
  a dispatch needs such an edit, split the deliverable: implement the writable half, and post an explicit
  owed-to-owner marker naming the exact file:line and the required wording. Never silently drop the half,
  and never weaken a gate just to avoid needing the edit. **A reviewer's signed rule-3c ACCEPT does NOT
  unlock the harness's interactive approval prompt** — `security.protected_instruction_files` defaults true
  and is deliberately NOT routed through the `--yolo`/allowlist gate (one-operation approval EVERY time,
  no persisted scope, fail-closed without a human channel). A headless lane still gets `BLOCKED: write to
  protected agent-instruction file(s) ... Silence is not consent` and must post a signed blocker with the
  denial text and exact diff, then stop. Do not treat review approval as write approval, and NEVER flip
  that config on your own to clear a queue. If the OWNER EXPLICITLY AUTHORIZES it, set
  `security.protected_instruction_files: false` in BOTH `~/.hermes/config.yaml` and
  `~/.hermes/profiles/<lane>/config.yaml` — a headless lane can read either one, so flipping only one is a
  silent no-op. Take timestamped `*.bak-<UTC>` backups FIRST and record the authorization + backup paths on
  the issue. Rule 3c itself is unchanged: design → signed reviewer verdict → implementer lands the exact
  approved text; only the mechanism of the final write changed.
  **Land that same setting in the repo's `agents/<lane>/config.yaml` mirror in the same delivery.** A host-only
  config change reds `make fleet-host-sync-check` as an owned-block drift (the flag is not a tolerated Hermes
  stamp), so flipping the host without the repo mirror trades one blocker for several divergences.
- **An auto-close can hide an undone half — verify the merged PR's DIFF, not its `Closes #` line.** GitHub
  closes an issue from any PR whose title/body carries the keyword, including a PR that implements only PART
  of the issue's scope. After a merge run `gh pr diff <n> --name-only` and confirm every file the issue named
  actually changed; a missing file means the issue was closed with work outstanding. Re-file that half as its
  own small issue with a handover instead of letting the close stand. When the missing half is a protected
  `AGENTS.md` row that was deliberately withheld pending owner authorization, grep the MERGED master for the
  exact approved needles (`git show origin/master:AGENTS.md | grep -c <needle>`); a zero count means the
  auto-close buried an undone rulebook landing. File the follow-up with BOTH approved texts quoted
  byte-for-byte and hand it to `owner`, then record the gap on the closed issue so it cannot read as fully
  delivered.
- **Lanes change locally and PUSH; CI verifies. Never have a lane pre-run the full containerised suite.**
  Owner directive #1423: A head's local `make validate` + whole `make test` costs 15–30 min inside the per-purpose
  Linux container; several lanes at once contend for ONE VM (load 5.8, the VM at 207% CPU) while each lane
  PROCESS idles at ~0% CPU in `sleep` polls. The same gates already run in GitHub Actions on `qa-validate`,
  which costs the host nothing. Dispatch a lane to run ONLY the fast offline checks
  (`python3 scripts/pr_body.py --check-body-file <f> --branch <b>`, `make lint`, the targeted unit module),
  push, confirm CI registered on the new head (`gh pr checks <n>`, `gh run view <id> --json jobs`), and
  report. Measured effect: the same class of delivery dropped from ~3h to ~23 min. Never write "gate green
  on the exact head before push" into a dispatch — that phrasing reproduces the waste.
- **Parallel by default — serialise ONLY the shared files.** Lanes whose TARGET FILES DIFFER run at the same
  time: worktrees isolate every tree and push-and-verify (#1423/#1424) removed the local-VM reason for a serial
  cap, so a serial "dispatch one at a time" habit is obsolete. The FILE collision is what remains, and the recent
  run proves the cost: #1418, #1432, #1445/#1449 and #1448 all edited the SAME two
  `agents/<lane>/skills/<lane>/SKILL.md` mirrors, so they raced — duplicated bullets reached master (#1448 merged
  duplicates as `0df63311`; three planner bullets measured x2), PRs went CONFLICTING, and auto-merge failed
  repeatedly. BEFORE spawning a lane, run `make dispatch-check ISSUE=<n> MACHINE=<user@host> CLAIMS="<path> <path>"`
  with EVERY repo-relative path it will write; it refuses when an ACTIVE registry lane already claims an
  overlapping path (#1458) or when ANOTHER host holds a newer ACTIVE working-claim on the issue thread (#1569).
  A refusal on a SHARED file means QUEUE this dispatch until that lane reports `done`; a refusal for any other
  reason (closed issue, merged PR, at the ceiling) stands too. Never start a second session on a branch another
  lane holds. If a collision still lands, measure the duplication on master and file a dedupe PR — do NOT force
  a third overlapping push.
- **Two hosts dispatching the same issue need a BOARD-VISIBLE ordering; a local timer cannot provide one.**
  The issue thread is the only surface every host shares. Before spawning, `make dispatch-check
  ISSUE=<n> MACHINE=<user@host>` must also refuse when another host has a NEWER ACTIVE working-claim
  (parse the signed `BOT <lane> · working on #` / `dispatch #` markers with their `user@host` machine line
  and createdAt); a per-host registry is invisible to other hosts and cannot prevent the collision.
  When another writer already moved a branch, a non-fast-forward rejection is the tell — STOP and report
  the handover rather than forcing a second push. Confirm the handover on the issue so nobody re-dispatches.
- **NEVER open a DRAFT PR — every fleet PR goes up READY FOR REVIEW.** A draft is invisible to reviewers and
  to auto-merge, so it stalls the board and hides finished work. Require a complete body plus `Closes #<id>`
  in BOTH title and body; if the work is unfinished, report status on the issue instead of opening a PR.
- **The `--query-file` is the DISPATCH PROMPT (`dispatch-<lane>-<issue>.txt`), never the comment body
  (`c-<id>.md`).** Launching with the comment file makes the lane read a board note as its task and die in
  seconds. Name prompts `dispatch-*`, comments `c-*`; print the first line before spawning. A killed
  one-shot lane can leave a registered empty worktree — check `git worktree list` before re-dispatching.
- **Post board notes with `gh issue comment <n> --body <text>` or `--body-file <path>` — `--comment` is not
  an issue-comment flag and exits 0 without posting.** A silent no-op looks identical to success in a
  shell batch. Re-read the thread after posting (`gh issue view <n> --comments --json comments`,
  last comment) whenever the record matters — a handover or ruling that was never posted leaves both
  hosts without the decision. On busy threads `gh api repos/<o>/<r>/issues/<n>/comments` returns only one page; use `--paginate`
  (`?per_page=100` is still one page and truncates a longer thread). The last item of a page-limited read is
  the tail of PAGE 1, not the real tail — never assert from it that a signed verdict or your own dispatch
  "never landed". When checking a SPECIFIC comment id, fetch it directly with
  `gh api repos/<o>/<r>/issues/comments/<id>`; a false "verdict missing" claim costs a re-post and erodes
  the thread record. **Batch-reading threads into Python needs the same care:** flatten each body in jq
  (`gsub("\n";" ")` in the `--jq` expression) before `json.loads`, or fetch one comment by id — raw
  newlines inside a body make `json.loads` fail with `Invalid control character` even though the shell
  command succeeded. **`gh pr close` has no `--comment-file`:** post the signed supersession reason with
  `gh pr comment <n> --body-file <path>` first, then close the PR.
- **Write the issue body to a draft and run `make issue-message-check BODY_FILE=<draft>` BEFORE `gh issue create` on a body declaring `message-pattern-opt-in` (issue #1730).** A non-zero verdict blocks the filing;
  repair the draft and re-run, never hand-edit a body after it landed. This is the same gate CI runs on
  `issues:opened/edited/reopened`, so a bot-filed body can no longer red `pr-closure` on its own shape.
- **A red naming a MISSING PRODUCT ARTIFACT is implementer work, not a rebase.** When `validate` fails
  because `findings/<issue>.md`, an OpenSpec change, or a test module is absent, the branch lacks output a
  lane was supposed to author — a rebase cannot fabricate it and must hand back. Measure whether the red is
  INHERITED (e.g. a seam moved from a root file to per-issue files after that branch's last green run) and
  dispatch `tll-implementer` to write the artifact on the existing branch; keep the rebase lane out of it.
**Subclass — OpenSpec lifecycle red.** qa-validate's `validate` job runs `make openspec-archive-check`
(the "OpenSpec lifecycle" step) on every PR head; `pr-closure` runs the same check on the PR head. A red
here is almost always the same fault: a PR that closes an issue with no binding OpenSpec change in the
head tree, or an existing change still unarchived. If the failing step label is `OpenSpec lifecycle`,
read the failing log's step name first, then dispatch `tll-implementer` with the artifact and the two fix
commands (`make openspec-new` + `Issue:`/`PR:` in proposal.md for a missing change; `make
openspec-record-pr` for an unarchived change; both followed by `make openspec-index`), before the red
lands — not after.
  **Require the artifact in the DISPATCH, not after the red.** When a PR body will say `Implements #<n>`,
  rule 6g binds, so name `findings/<issue>.md` as a delivery item up front; a missing findings file reddens
  `validate` in seconds and costs a whole CI cycle to discover.
- **Before calling a lane slow, separate WALL-CLOCK from CPU and count the containers.** A lane can sit for
  hours at ~0% CPU in `sleep` polls while its real work runs in `docker run` containers on the shared VM.
  `ps -Ao pid,pcpu,time,etime,command` shows seconds of CPU across a 2h runtime; `docker ps` shows the actual
  workers AND any LEAKED runner (one left up for days silently holds VM resources — remove it). Only then
  judge: kill a leaked container, cap concurrency, or let a gate finish. Never kill a live lane to "fix"
  latency without first naming what it is waiting on.
- **Cron fires run WITHOUT approval and block arbitrary code: `execute_code` is refused, and so are
  shell heredocs and inline interpreters (`python3 -c "…"`, `<<EOF`).** Write probe scripts to the
  profile scratch (`~/.hermes/profiles/tll-planner/cache/scratch/<name>.py`) with `write_file`, then run
  `python3 <path>`; use `gh api … --jq` for one-off reads. Never pipe a `make`/probe through a
  truncating filter and trust its exit status — the pipeline returns the LAST command's status, so re-run
  without the pipe when a verdict matters.
- **Do NOT "sync" a host by wiping Hermes runtime stamps or unlanded skill notes.**
  `make fleet-host-sync-check BASE=origin/master` reds on runtime stamps in a lane `config.yaml`
  (Hermes state the gate itself must tolerate — #1401) and on host `SKILL.md` pitfall notes that are
  legitimately AHEAD of master. Deleting the stamp locally only masks the gate bug. Take timestamped
  backups (`*.bak-<UTC>`), leave the files, and route the two halves through the normal paths: the gate
  fix via its own PR, the note-landing via a reviewed change.
- **A PR with "no checks reported" is NEVER green — it is a never-started head.** The seam: `gh pr
  checks <n>` answers `no checks reported on the '<branch>' branch`; enumerate
  `gh api repos/<o>/<r>/actions/runs?head_sha=<headSha>` and `gh run view <id> --json jobs` for EVERY
  run at that sha. Zero runs OR only `completed/action_required` runs with 0 jobs and actor
  `github-actions[bot]` is the same shape — a job-token push schedules no jobs, and it can leave two
  such runs, so do not infer the shape from `gh run list --commit` showing "no runs" alone. The commit
  author name is NOT proof of a workflow-triggering push: `gh api repos/<o>/<r>/commits/<sha> --jq
  .author.login` can name the owner while the push path still scheduled no workflows. Always enumerate
  `gh api repos/<o>/<r>/actions/runs?head_sha=<headSha>` and check `total_count` plus each run's job
  count; only real jobs are a verdict. Post ONE
  failure report naming the run urls, the head and the evidence, then hand the recovery to the branch's
  OWNER lane: re-push ONLY that branch with an owner-git-identity empty commit through the owner-PAT
  remote and prove the new run has real jobs. Never report such a head as green, and never start a
  second session on a branch another lane already holds. Put the owner identity and owner-PAT remote
  in every bounded-rebase ruling for a branch that has already ghosted: a rebase pushed by the bot
  actor recreates the zero-job head. Verify the new head's job count before accepting any bookend. (#1115)
- **A green `validate` proves nothing when `master` moved during the run — the merge-tree OpenSpec check
  races EVERY open PR.** `qa-validate` merges the PR with `origin/master` and runs `make
  openspec-index-check` on the RESULT, so any master advance between a PR's cut and its run conflicts on
  the generated `OPENSPEC.md` (`[merge-tree-index] MERGE CONFLICT`). The diagnostic seam: a `validate` that
  PASSED had NO `master -> origin/master` update during the run; every failure at that step HAD one, and the
  3-way blob merge is clean locally. Treat it as a RACE, not a code defect — rebase onto the fetched tip,
  regenerate the index (`python3 scripts/openspec_index.py --write`), re-push. Do not "fix" the branch's own
  logic, and do not rebase repeatedly while master keeps moving under the run: say so and let the gate land
  on a stationary tip. Expect several rebases per PR while the board is busy. When the SAME race has
  re-dirtied one PR more than twice, stop rebasing that PR: record the sha where CI was actually green,
  file ONE evidence-backed issue for the gate seam instead of one per rebase, and hold the PR until the
  gate fix lands or the owner rules — endless bounded rebases are churn, not throughput.
- **A gate cancelled by `timeout-minutes` is not a code defect and must not be re-run into the same cap —
  sequence behind the filed timeout fix.** Read the job's `conclusion` and its last step before ruling:
  `cancelled` at the exact cap with a still-running unit suite is a capacity limit, not a failing test.
  Hold the issue with that evidence on the thread; do not `gh run rerun` and do not ask a lane to re-push
  merely to re-trigger CI. When the timeout fix lands, rebase the held PR onto that tip before re-triggering
  — GitHub runs the workflow from the PR's own tree, so a re-push on the old base still carries the old
  limit and burns the full cap again. A fix raised on master cannot help a branch that has not rebased.
- **Before bulk-closing stale keeper PRs, measure the generated artifacts on master AND confirm each
  diff is generated-only.** In a detached worktree at the fetched tip run `python3
  scripts/openspec_index.py --check` and `python3 scripts/architecture_check.py`; if both report current,
  keeper PRs whose only diff is `OPENSPEC.md` / `ARCHITECTURE.md` have nothing left to land. Check
  `gh pr diff <n> --name-only` per PR — a keeper carrying a unique fix must be kept. Close with a signed
  reason naming the measured sha and 'reopen if you disagree'; never merge a moot PR by hand.
- **A keeper whose target archived count is BELOW master's is SUPERSEDED — no rebase, no force-push.**
  Generated-artifact-only keeper PRs (`OPENSPEC.md` / `ARCHITECTURE.md` regeneration) go stale when master
  advances past them. Measure READ-ONLY, without executing a local gate: `git show
  origin/master:OPENSPEC.md | grep -m1 'Active changes:'` for master's count and `gh pr diff <n> --patch`
  for the keeper's one-line target. If master is already ahead, close the PR as superseded with a signed
  reason rather than producing an empty re-anchor or a no-op commit.
- **Before dispatching an implementation of a filed defect, verify the gap STILL EXISTS on fetched master.**
  A filed issue can already be fixed by another host or the Actions lane while it sits in the queue.
  Read `gh issue view <n> --json state` first, then `git show origin/master:<file>` for the named artifact
  (or run the named test in a detached worktree at the fetched sha). If the fix is already on master, post
  the measurement on the issue and STOP — opening a second PR would be unrelated churn against a closed
  issue. This is the same verification as the superseded-keeper check, applied to code fixes.
- **Master's own push run can go green and SUPERSEDE a filed `validate`/`openspec-index` failure.**
  Before dispatching a fix for a filed pipeline-failure issue (#1412/#1413 class), re-measure the newest
  push-to-master `qa-validate` run at the CURRENT tip: `validate` success with `index-repair` skipped
  (`DRIFT=none`) means the defect is already remedied and the issue needs a verify-and-close, not a new
  fix.
- **The failure filer can quote expected negative-test chatter as the error block — read the job's
  `##[error]` line before trusting a filed body.** `make pipeline-failure-issue` extracts from a log region
  and can pick up `FAIL:` lines that are the EXPECTED output of a guard test's planted fixture inside a
  module that then reports `PASSED n | FAILED 0`. Measured on run `45231126714` (filed #1450): the body
  quoted `FAIL: m1: measurement_model_aliases is not a list`, while the job's ONLY `##[error]` was the
  final `OpenSpec index on the merge tree` step (`[merge-tree-index] MERGE CONFLICT`). Grep the job log for
  `##[error]` and the step `##[group]` headers to name the REAL failing step, and post a correction comment
  on the filed issue when its quoted block misleads.
- **A recurring gate red files one near-identical issue per run — sweep the flood before dispatching fixes.**
  Check master's newest push runs first: if they are green, the old filings are historical, not open defects.
  Group them by root cause and close or consolidate the duplicates with a signed reason; dispatch one fix
  for the distinct root, never one per filing. Do not confuse those auto-filed `tech-debt` items with the
  fleet's own `enhancement` board.
- **Host↔master `SKILL.md` divergence is TWO-DIRECTIONAL — never byte-copy host files into master.**
  Measured on #1446/#1455 at `0df63311`: host-only bullets are genuinely new, but the host also LACKS
  newer master sections (the `## Delivery procedure` block), and copying host bytes verbatim DELETES lines
  `tests/test_fleet_lifecycle.py` pins (`test_lane_skills_carry_the_push_and_verify_rule`) → measured
  `FAIL 14`. Land only the additive host-only notes, de-duplicate what earlier PRs already carried, then
  refresh the hosts FROM master once nothing host-unique remains.
  - **Measure a host-sync divergence against the RIGHT repo path — `agents/<lane>/skills/<lane>/SKILL.md`.**
    `git show origin/master:tll-<lane>/skills/...` silently answers EMPTY (the profiles live under `agents/`), so the
    diff counts every host line as a divergence (measured 2026-11-23: bogus 471-line "delta" vs a real 99). Read the
    correct blob, or the sync verdict is noise.
- **`gh issue close --reason duplicate --duplicate-of <n>`** — the literal reason is `duplicate`
  (`not_planned` is INVALID and errors). Three filings of one step defect in one evening
  (#1439/#1452/#1453) consolidate into ONE dispatch on the instance issue, mirroring each filing's
  distinct Done-when onto it; do not leave parallel trackers for the same red.
- **Overlapping watcher ticks can run TWO planner sessions at once — re-scan before filing/dispatching.**
  Measured 2026-11-23: two ticks filed the SAME change as #1455 and #1456 five seconds apart and each
  started an implementer on the same mirrors. Before filing or dispatching, search the newest issues for a
  sibling filed minutes earlier; consolidate (close the duplicate, withdraw your own lane BEFORE it pushes)
  rather than letting two PRs race on one file pair. Re-read the thread once more AFTER posting your own
  dispatch: a newer implementer status may already report the fix pushed. In that case post a signed
  back-off naming the existing head and kill the lane process you spawned before it claims or pushes —
  a dispatch-check ALLOW only proves the issue is open, not that the work is still undone. When the other
  session already holds the live items, do NOT re-dispatch them: take the distinct stalled item (a
  conflicting PR with no recent claim, a stale keeper) and say that scope in your dispatch comment so the
  two sessions cannot race. A missing `hermes -p tll-*` process does not make a signed claim stale — the
  claim may come from another host or a session that has exited; the newest signed claim on the shared
  thread is the source of truth.
- **Master can move several times inside one cycle — re-measure before every ruling.** A dispatch's
  premise can be void by the time the lane reads it (#1448 merged while its implementer was still awaiting
  a ruling). Re-check `gh pr view <n> --json state,headRefOid` and `make dispatch-check ISSUE=<n>` before
  answering a lane's question, and bind every verdict to the sha actually reviewed. **Apply the same
  re-measure in the dispatch-to-launch window:** after posting a dispatch but before spawning the lane,
  re-read the newest comment and the PR head; if a newer state note moved the head, post a signed
  correction on the issue and update the lane's query file to the new head and CI run ids before launch.
  A reviewer started with a stale head rules on code that is no longer on the PR. The same applies to the
  BRANCH: an empty CI-retrigger commit can move an owned branch between measurement and push. Re-read
  `git ls-remote origin <branch>`, pin `--force-with-lease` to that fetched ref, and STOP if it moved again.
  Before ordering a force-push over a branch, confirm no live lane still owns it — a non-fast-forward
  rejection during a rebase is the tell, and the correct response is a signed STOP plus an ownership ruling
  on the shared thread, not a retry.
- **Re-read the current head before answering a lane that says it is blocked or waiting for a ruling.** By the time you answer, another host may have pushed the branch, merged the PR, or already recovered the CI. Measure `gh pr view <n> --json state,headRefOid,mergeable`, `gh pr checks <n>`, and the newest issue comment first. Then post ONE explicit ownership ruling on the shared thread — "not handed back, lane X is live" / "handed back, push held head with lease pinned to <sha>" — so nobody force-pushes over a live writer and nobody re-dispatches a finished issue.
- **A lane a planner cron starts can be hard-interrupted when that cron session ends — verify liveness, then RESUME.** Measured #1495 (2026-11-24): the implementer ran 599 s, cut its worktree and posted its claim, then its profile log recorded `Interrupt requested (hard): explicit stop requested` with NO commit and NO PR, and no `tll-*` process survived. Launch lanes with `terminal(background=true, persist_on_release=true)`, and before trusting that work continues check `ps -p <pid>` AND the lane's `logs/agent.log` for fresh API calls. On death, run `make dispatch-check ISSUE=<n>` and dispatch the bounded RESUME above — never a second implementation.

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

- **Open every PR READY (never draft) — owner directive 2026-11-24.** Every fleet PR goes up ready for review. A draft is invisible to reviewers and to `auto-merge` (`scripts/auto_merge_rebase.py` verdict `draft` → "untouched"), so it silently stalls the board and hides finished work. When dispatching, tell the lane to open the PR ready; if the work is genuinely unfinished, report status on the issue instead of opening a PR at all. `make pr-draft-check` names a bound draft PR with its issue.

- Every fix or improvement is synced into the repo as BOTH its own issue (or the existing bound issue)
  AND an implementing PR before it is called done. A local change, a chat message, or a branch alone is
  not a delivery. Verify the merge and the issue's close state; if a fix landed without a PR, file one.
- Every lane that opens a PR must ship: `Closes #<id>` appears in BOTH the PR **title**
  and the PR **body** content (owner clarification — not title-only, not body-only).
  Title carries the change + issue id; body repeats `Closes #<id>`; merged PRs must close
  the issue they implemented. When a reviewer confirms a gap in the GUARD THIS PR ITSELF ADDED, route the fix
  as an AMENDMENT of that still-open PR, not a second competing PR: push to its existing branch, and ADD the
  new issue's `Closes #<n>` line to the body ALONGSIDE the original one (never replace it). A second PR on
  the same generated files would race the first.
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

## OpenSpec lifecycle gate (make openspec-archive-check)

`qa-validate`'s `validate` job runs `make openspec-archive-check` (its "OpenSpec lifecycle" step) on every
PR head, and `pr-closure` runs the same check on the PR head. It REFUSES a PR whose head tree has no
OpenSpec change binding the issue the PR closes, or whose change exists but sits unarchived.

Diagnostic recipe for a PR red at `validate` on `OpenSpec lifecycle`:
1. Reproduce at the exact head and read the failing step's log. Name the failing step label before
   dispatching — a PR with no checks reported is a never-started head, not an OpenSpec defect.
2. List the PR's `Closes #<n>` bindings in title and body. For every bound issue, confirm an ACTIVE
   (not merely present) OpenSpec change exists in the head tree: `git ls-tree origin/master
   openspec/changes/`, then `git show origin/master:openspec/changes/<slug>/proposal.md` to read its
   `Issue:` line — absent, wrong, or unarchived, `make openspec-archive-check` exits 1 (`NO OpenSpec
   change` when missing; an existing change only passes once it is ARCHIVED).
3. Fix it with the two-command set, not a rebase: for a missing change, `make openspec-new NAME=<kebab>`
   and bind `Issue:` + `PR:` in the proposal, then `make openspec-index` to rebuild `OPENSPEC.md`; for an
   existing but unarchived change, `make openspec-record-pr ISSUE=<n> PR=<pr>` (records AND archives),
   then `make openspec-index`.
4. Verify locally before push: `make openspec-check` green, and the PR still carries its `Closes #<id>`
   in BOTH title and body. Push and confirm CI registered on the new SHA: `gh pr checks <n>`,
   `gh run view <id> --json jobs` — the `validate` job re-runs on the new head, so the gate must turn
   green there. If `validate` stays red, fix the CODE from the job log, not the trigger.
5. Re-read the issue thread after the dispatch — the comment is the record; a PR comment alone is not a
   delivery. The implementer lane's work hands to `tll-reviewer` for the verdict.

6. Verify the archive verdict against the REAL `origin/master` tree, not the PR head's report: `git
   show origin/master:OPENSPEC.md` → the `## Active changes` table must no longer list the change, the
   `## Archived changes` table must list it, AND the `active=`/`archived=` counts printed by
   `make openspec-index` must match the disk (dir listing of `openspec/changes/archive/`). A padded
   archive dir with wrong counts, or a change still listed in the active table, means the archive did
   not land. The PR's commit message or issue comment saying "archived" does not satisfy this.
Class outcome: a PR closing an issue with no binding OpenSpec change, or an existing OpenSpec change
still unarchived, is the one root cause behind several red `validate` jobs this cycle. The implementer
lanes applied the same two-command fix on the same `origin/master` base sha, and the reviewer verdicts
then closed the issues on the corrected heads. This is the `missing-artifact` class, so the rebase lane
must NOT fabricate the change — hand the defect to `tll-implementer` with the artifact in the dispatch,
before the red lands, same as any other red named a missing product artifact.

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

## Rule 3c landings (design → review → write)

An edit to `AGENTS.md §7b/§8` or any `agents/*/SOUL.md` is review-required. Run the three steps in order
and post each on the issue's OWN thread:

1. **Architect design** — a signed finding with the EXACT proposed row text, its section anchor, the
   names-only test that pins it, and its reconciliation against other rulebook landings (disjoint anchors,
   no duplicate/contradiction). No tree write.
2. **Reviewer sign-off** — a signed `done` carrying the approved text byte-for-byte. This is PROCESS
   approval only; it does not unlock the harness protected-write prompt (see the pitfall above).
3. **Implementer write** — land the approved text VERBATIM, never re-worded from memory; carry the shared
   note clause in the order ALREADY PRESENT on the landed head, taking `git show origin/master:AGENTS.md`
   as the source of truth — never an order quoted in a dispatch, a design, or chat (a planner who guessed the
   sequence sent a rebase lane the wrong order and had to correct it in-thread). On a rebase of a rulebook PR,
   resolve a shared append-only line as a UNION of all clauses, not `--ours`/`--theirs`; verify every sibling
   clause is still present and each approved needle occurs exactly once before pushing. `Closes #<id>` in
   title AND body; open READY. If still refused, post a signed blocker with the denial text and exact diff,
   then stop.

Group independent rulebook changes into separate small issues rather than bundling them into a debt
landing whose own sign-off covered different text. Measure the approved strings' current occurrence count
in `AGENTS.md` first (a zero count means purely additive; a non-zero count means a duplicate).

- **A missing needle in an EXISTING row usually means extend that row in place, not add a new one.** Check
  the row's real test function list against the tests on disk; if one implemented test is simply un-named,
  replace that single row with the approved text and verify the row/pipe-line count is unchanged. A new row
  would duplicate the guard and break the names-only inventory.
- **A rulebook row landing normally owes its own OpenSpec change — prove it before accepting "none owed".**
  Run `python3 scripts/openspec_archive_check.py --pr <n>` on the branch: a `NO OpenSpec change` failure
  means the change is required even though the edit is docs-only. Bind it to the issue and archive it on the
  same branch, or `validate` reds at the lifecycle gate after the design and review are otherwise complete.
- **A names-only pin that asserts a shared append-only line ENDS with its own clause is brittle by
  construction.** Any later clause appended by another landing breaks it. Require presence plus ascending
  order instead, and prove both orders pass while a missing/out-of-order needle still reds. When two
  approved pins genuinely contradict, keep the order of the LANDED head and dispatch the relaxation as its
  own small amendment to the still-open PR — never move the shared line to satisfy the older pin.

## Fleet claim/read/report protocol (owner-mandated, #703)

Spread responsibility: the planner delegates; every lane posts a signed working-claim COMMENT on the issue
BEFORE starting; each bot READS the issue thread first to detect another lane's LIVE claim on the same issue;
if a collision exists, the bot reports it to the planner (never two writers on one issue) and the planner
re-dispatches. Every lane fetches latest `origin/master` before measuring and starts work in a worktree.
Verify each lane applied it on #703.

## Handover protocol (owner-mandated, issue #1189)

Every lane hands over on the issue thread, so the board can be followed without re-reading each thread:

- **Dispatch names the handover.** A dispatch comment carries the lane, the fetched `origin/master` sha, what done means, and the handover target:
  `BOT tll-planner · dispatch #<id> · lane <lane> · base <sha> · done <criteria> · handover <next-lane|owner>`.
  `done <criteria>` is the push-and-verify sequence — the fast offline checks, the push, and CI registered on the new SHA — never a pre-push full local gate (owner directive 2026-11-23, issue #1423).
- **A lane finishes with a signed handover comment** on the issue's OWN thread:
  `BOT <lane> · done #<id> · handover <next-lane|owner|none> · <the one next action>`.
  `handover` names the ONE lane that owns the next step (`tll-planner` re-triage, `tll-implementer` write, `tll-tester` verdict, `owner` a human decision); `none` only when the issue is fully done.
- **Progress comments are the record.** A lane working across sessions posts state at each step, not only the opening claim.
- **After a delivery, re-read the issue board and claim the oldest unclaimed actionable issue, or file an evidence-backed issue with a handover to `tll-planner`.** A `done`/`handover` comment followed by silence is not a delivery.
- **The fleet spans several machines.** The issue thread is the ONE shared board across hosts: a lane reads it first to see which lane on ANY machine holds a live claim, and hands over on it. Never two lanes on one issue.
- **Claim twice before starting (race guard).** A lane posts its signed working-claim, waits about a minute, re-reads the thread, and starts only if its claim is still the newest; a newer claim by another lane on any machine wins and the first lane backs off.
- **A lane never works outside its remit** — it files or comments and hands over.
- **The board is the issue thread itself.** The parent fleet issue #682 is closed; do not keep a stale parent reference. Keep each open issue's thread current: who commented, which lane is in progress, what is next. For cross-host claim races and duplicate PRs use the decision table in `references/multi-host-coordination.md`.

### Read the comments to delegate (owner-mandated, issue #1209)

- **Comment on the issue BEFORE you do the work.** Every lane — including this one — posts its signed comment on the issue thread before opening a branch, starting a review, giving a verdict or rebasing a PR. The planner orchestrates from those comments; there is no gap between lanes.
- **While a test or CI gate runs, post a status comment on the ISSUE (issue #1232).** Name your machine as `user@hostname` (e.g. `asimov@omarchy`), then say what you are doing, what you are waiting for and which issue/PR you can help with next; repeat on each state change. One comment per state: this does not replace the claim, the PR comment or the `done #<id> · handover <...>` comment, and it never claims an issue another machine owns. The planner reads these notes to delegate; the other host reads them to decide what to take next.
- **Read before you dispatch.** Before naming a lane, re-read the issue's own comments
  and take the NEWEST signed handover as the state. Dispatch from that comment, not
  from the issue body: `BOT tll-planner · dispatch #<id> · lane <lane> · base <sha> ·
  done <criteria> · handover <next> · answering <comment-id>`. Naming the comment you
  answered is what lets the next machine follow the chain without re-reading it.
- **A PR is never the handover.** When an implementer opens a PR it posts on the ISSUE:
  `BOT <lane> · pr #<id> · PR #<n> · base <sha> · handover tll-reviewer · <next>`.
  A PR comment alone is not a record — the planner reads the issue, not the PR.
- **The reviewer answers on that same issue:** `BOT <lane> · reviewing #<id> · PR #<n> ·
  handover <tll-implementer|owner>` then a signed `done #<id> · handover <...>` comment.
  A red check hands back to `tll-implementer`; a human decision hands to `owner`.
- **Always follow up on the issue.** Every fix, verdict, re-dispatch and closure gets a
  comment on the issue's own thread; the bots read and update that thread at each
  handover. The issue stays open as the follow-up until `handover none` is posted.
- **The board note also names the PRs AWAITING REVIEW, and hands each to `tll-reviewer`
  by name** (issue #1261). Producer lanes cycle faster than reviewer lanes, so an open-PR
  backlog grows while every issue already reads "claimed" — measured: 14 PRs open at once
  with #1241/#1242/#1247/#1248/#1254/#1255/#1257 all waiting for a first-review slot.
  The note therefore carries, for each open PR with no reviewer handover yet: the PR
  number, its head sha and base, and `handover tll-reviewer`.
- **Spend review capacity BEFORE producing new PRs.** An issue with no PR is dispatched to
  an implementer; an open PR awaiting review is dispatched to `tll-reviewer` FIRST. Adding
  producers without adding reviewers grows the backlog, not the merge rate.

## Fleet state (active issues)

- **#689** move the per-engine measurement store out of `data/models.json` — **landed**. Store is now
  top-level `engines` registry + `models` (a list whose measurement rows live in
  `engagement.seen_posts[]`, not a per-model `engines[]`); verify the flattened view equals the old inline
  view (equal t/s rows per model) via `--render-only` byte-diff (guards #463/#525).
- **#690** worktree-default fleet convention.
- **#691** propose a `tll-docs` lane (schema⇄contract sync + architecture/how-it-works doc).
- **#1775** (fleet-sync directive, delivered): planner's rulebook behaviour + all 8 lane `SOUL.md` + skills
  re-synced to base blob `37c6d88150fdb73fd0583a59099aee0b418d7927` (`make fleet-host-sync-check BASE=origin/master`
  prints OK, exit 0); the sync issue thread carries the start/dispatch/done confirmation (the owner's
  "no human intervention needed" form). No further work remains.
- Successors of this distribution: `tll-architect`, `tll-implementer`, `tll-reviewer`, `tll-security`, `tll-docs` (lane stood up by issue #1396; profile provisioning is an owner act).

## Measurement store (post-#689 split — landed)

The #689 store split is now live on `master`: `data/models.json` carries a top-level `engines` registry
plus `models` (a list). MEASURED 2026-11-23 at `f2b3db89`: the per-(model, engine, source_post) measurement
rows are NOT a model-level `engines[]` — they are `engagement.seen_posts[]` (each row: `url`, `date`,
`engine`, `tps`, `hardware`, `quant`, per-post counters). Judge sync honesty by that shape — models catalog,
engine registry count, and total `seen_posts` rows (not the pre-split "inline engines[] for N models"
framing). The standing requirement
after any further change: keep the flattened/regenerated view equal to the previous inline view so no
measurement is lost (guards #463/#525), highest t/s per (model, engine, vram/ram fit) sorts top, and no new
timer — dispatch to `tll-architect` (design) then `tll-implementer` (write).
