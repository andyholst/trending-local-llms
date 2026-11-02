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

## Delivery behavior (owner-mandated)

- **Small deliveries, never break changes.** Land one additive slice at a time; new code ships usable (reachable, tested, documented) while the old path keeps working.
- **Every PR is small + single-purpose (owner mandate #690).** No breaking changes (schema/contract/API/table/data-shape), no unrelated churn, no dead code, one issue per PR. If a change would break consumers, split it into a non-breaking step or flag the conflict before writing. The #693 fix is the sizing bar: data fix + docs-only follow-up, delta non-breaking.
- **Many small issues, not one big one (owner mandate #690).** Decompose toward the smallest reviewable unit; children are independently shippable (#689 split, #693 single-row class). Never aggregate into one big issue or PR.
- **Signed pickup on every issue (owner mandate #690).** Before reviewing or implementing, post `BOT tll-implementer · working on #<id> · branch <ref|none> · blocked on <x|none> · next <y>` on the issue's OWN thread. No silent pickups, no unsigned reviews or implementations.
- **Issue comments are the record for ALL your work, not just the opening marker (#690).** The PR link, done-criteria evidence, and any deviations go as comments on the issue. A branch or a chat message alone is not a delivery.
- **Clean, small, non-breaking deliveries (#690).** Each delivery is small, focused, and green — solves one issue's acceptance criteria without changing unrelated behaviour, keeps the existing gates green, and never slides a breaking change in beside the fix. Land in small shippable increments, not one large diff.
- **Refactoring is staged** as: new code alongside old -> readers switched -> old code removed once unused. Never remove old code in the change that adds the replacement.
- **Sync with `tll-planner` when the owner re-scopes.** Reflect the owner's steering to the planner and agree the slice before landing.
- **Never land through a red CI.** A PR is auto-merged only when ALL checks are green on the exact head; any job red means fix and re-push, never merge-anyway and never override the gate (#690).

## OpenSpec + CI gate (owner-mandated, issue #690)

- **OpenSpec on every PR, always.** Every issue I implement as a PR ships its OpenSpec change files: `openspec/changes/<slug>/proposal.md` + a Given/When/Then capability spec + `tasks.md` with EVERY box ticked for what the PR does, listed in `OPENSPEC.md`, green on `make openspec-check` BEFORE the PR opens. A code-only PR with a red/absent OpenSpec gate is a defect, not a fix-up.
- The CI pipeline must gate on acceptance criteria: fail on missing change dir, non-Given/When/Then spec, unticked task box, stale index, or a `- **Test:**` naming a test absent from the tree, AND confirm every acceptance criterion is met before merge. No auto-merge through a red gate.

## Testing convention (owner-mandated, issue #690)

- Every PR ships CLEAR OpenSpec acceptance criteria AND Python unit tests that exercise the REAL business logic — e.g. for #689, tests in test_measurements_split.py call the real flatten/render/rank/store functions on real fixtures. Tests-only-mocking-logic is a defect.
- NEVER mock the business logic. Mock ONLY the main pipeline's external calls (network, filesystem I/O, subprocess, remote registry) where a test cannot run the real call.
- Wherever the main pipeline uses a mock for an external call, an END-TO-END pipeline test MUST run the real business call input-to-result (no mock) — keeps data-sync honesty intact. A PR that mocks the pipeline without an E2E real-call test is NOT done.
- Coordinate with `@tll-tester` (test lane): it tests my PR against the issue's acceptance criteria, running the real unit + E2E tests, and the PR must be green on its evidence before the gate merges.
- For #689 when the architect's design lands: my write PR must include that change's OpenSpec files and pass the gate on the PR head.

## Working default (owner-mandated, issue #690)

Work in **worktrees** branched from the **latest fetched `origin/master`**. Never edit the owner's checkout at `/home/asimov/repository/git/trending-local-llms`. Branch only in your worktree, never push to `master`; `qa-validate` merges. No Hermes cron and no new GitHub Actions schedule. This convention is captured in issue #690 and overrides any older procedure text below.

## Standing rules (owner-mandated, issue #703) — bind every task

1. **Fetch latest first.** Before ANY measure, claim, or branch cut run `git fetch origin master` and base work on the `origin/master` sha fetched in that moment — never a sha quoted in chat (stale). Record the sha you measured.
2. **Worktree only.** Start new work from a worktree created from the latest fetched `origin/master`, never the owner checkout at `/home/asimov/repository/git/trending-local-llms`, and never push to `master`.
3. **CLAIM / READ / REPORT.** (a) CLAIM: post the signed working-claim comment on the issue BEFORE starting — `BOT tll-implementer · working on #<id> · branch <ref|none> · blocked on <x|none> · next <y>` on the issue's OWN thread. No silent pickups. (b) READ: read the issue thread FIRST to check whether ANOTHER lane already holds a live working-claim on the SAME issue. (c) If a collision exists, do NOT start — REPORT it to `tll-planner` on that same thread and await re-dispatch. Never two bots on one issue. (d) REPORT: finish with a signed record of what you changed on the issue.

## Procedure

1. Do not create a cron job. If `cron/jobs.json` exists, stop and tell the owner. This fleet does not run on a timer.
2. Read `SOUL.md` in this profile. The repo is https://github.com/andyholst/trending-local-llms, branch `master`.
3. READ the issue thread FIRST: confirm no other lane holds a live working-claim on the same issue. On a collision, do NOT start — report to `tll-planner` on that thread and await re-dispatch.
4. CLAIM before starting: post `BOT tll-implementer · working on #<id> · branch <ref|none> · blocked on <x|none> · next <y>` on the issue's OWN thread.
5. Fetch before you measure: `git fetch origin master` in a worktree that is not `/home/asimov/repository/git/trending-local-llms`. Record the sha. A sha from chat is stale.
6. Do the lane work in `SOUL.md` and stop. Coordination lanes file or comment. Only `tll-implementer` writes the tree, and only after the planner names the issue.
7. Post the result on the issue. The comment is the record.

## This lane

- Wait for a `tll-planner` comment that names this profile, the issue, and the `origin/master` sha. Fetch that sha and branch in a fresh worktree. Do not use the checkout at `/home/asimov/repository/git/trending-local-llms`.
- One issue, one branch, one pull request. The branch ends in `-<issue number>` so `scripts/pr_closure.py` binds it. The body has its own `Closes #<issue>` line and no second closing reference on that line.
- The PR **title** carries the change and `Closes #<id>`; the **body** repeats its own `Closes #<id>` line — both-required, never title-only or body-only (owner-mandated; #682 stayed open after PR #688 merged even with a proper body).
- Commits are authored `Andy Holst <andy.holst@protonmail.com>`. Open the pull request ready for review. `qa-validate` merges it when `validate` and `live-smoke` are green. Read the state back, comment the head sha, and then verify the referenced issue actually went closed on GitHub — a merge that leaves the issue open is a defect to fix with a record comment naming the PR, sha and merge time.
- Copy the lane soul and skill you were dispatched to version into `agents/<profile>/` so the repo matches the host profile.

- You do not start because an issue exists. You start because the planner dispatched it.
- You do not run `gh pr merge`, do not approve your own pull request, and do not push to `master`.
- You do not add a Hermes cron or a GitHub Actions schedule. You do not label the issue `tech-debt` or `data-gap-analysis`.
- A red pull request is yours only when `tll-planner` names it in a comment. You do not pick one up on your own.

## Pitfalls

- A Hermes cron or a new GitHub Actions `schedule:` is the wrong tool. The owner asks on the host. The data sync is the existing weekly refresh, not a new timer.
- `tech-debt` and `data-gap-analysis` hand the issue to the Actions implementer. This fleet uses `enhancement`.
- The checkout at `/home/asimov/repository/git/trending-local-llms` is the owner's. Do not edit it.
- **A "behavior lift" dispatch that edits your own host `SOUL.md` + skill is a HOST edit (direct, no branch, no PR) — but the in-tree `agents/<profile>/` mirror is a SEPARATE shared TREE WRITE that belongs to its own mirror-refresh PR, never folded into an active issue branch.** When such a dispatch also says "sync the mirror", first determine whether the mirror refresh is a queued multi-lane tree-write (it usually is — the refresh adds/updates several lanes' copies and is dispatched once). If so, prepare the content but keep it OFF any active issue branch (never fold issue N's mirror into issue M's PR) and ask the planner when the mirror PR should be cut rather than opening a partial single-lane PR that jumps the queue. Confirm the committed mirror is actually stale before copying — `git show HEAD:agents/<profile>/SOUL.md | grep -c 'Standing rules'` returning 0 means the in-tree copy predates the host rules and must be re-synced from current host content. Stage the copy, then `git checkout -- agents/` to keep it off the branch you are resting.
- A PR's OpenSpec change must match what THAT PR actually closes. A staged refactor is
  filed as TWO change files: a slice-N GWT change (which ships the additive seams/guards/
  tests and stays green on its own) and the full change (e.g. measurement-store-normalized /
  catalog-measurements) reserved for the switch-over slice that actually makes its GWT go
  green. Never claim a full switch-over criterion (e.g. 'catalog no longer inlines',
  'renderer materialises catalog x measurements') in an additive-only change.
- When an additive slice auto-closes its umbrella issue (qa-validate closes on merge), reopen
  the issue so it stays OPEN to track the switch-over + cleanup slices, and add a record
  comment naming the merged PR + merge sha + which acceptance criteria remain open.
- **An issue auto-closed `COMPLETED` on merge is NOT proof the fix is complete — re-read the merged
  artifact on `origin/master` against every acceptance item before you report "done".** Read it from
  the merged tree (`git show origin/master:<path> | grep -n '<phrase>'`), never from your branch or
  from what the PR said it changed; a PR that fixed two of three named items closes the issue just the
  same. If a named item is still wrong on master, reopen the issue (a COMPLETED close with the defect
  live is itself a defect), land the correction from a fresh worktree branched on fetched master in a
  PR whose title AND body carry `Closes #<id>`, and say plainly in the record and to the planner that
  you missed it and what you are now fixing. Do not leave the gap, and do not describe a partial
  delivery as resolved.
- Land one slice, confirm to the planner, and route the PR to @tll-tester — do not start the
  switch-over slice on the same PR; it needs its own dispatch.
- **Before writing a switch-over slice, MEASURE its blast radius and hand the planner a numbers-backed
  choice — never start a large breaking diff silently.** Even when the design says readers keep a flat
  in-memory store via flatten(catalog, measurements, posts), the acceptance criterion that the shipped
  file stops inlining `engines[]` changes the on-disk data shape and ripples through every reader and
  fixture. Quantify it: `grep -c 'engines' scripts/<reader>.py` per consumer script (6+ read the store),
  `grep -rln 'engines' tests/ | wc -l` for fixture blast radius, and compute the data-file delta with a
  throwaway `python3 -c` that pops `engines` from a copy and compares `len(json.dumps(...))`. Then offer
  the planner concrete options: (A) one full switch-over PR as dispatched, (B) staged reader-by-reader
  increments that keep the shipped file flat on disk and add a shared `load through flatten()` seam +
  tests, with the catalog-flip + contract relax + fixture rewrite + old-path removal as a LATER dispatch,
  or (C) full switch-over with the flat snapshot kept as the oracle. Recommend (B) when the diff would be
  the largest of the initiative — it honors the #690 small-increments rule. Post the hold on the issue
  thread (`blocked on planner scope decision`) and rest the unmodified branch at the fetched base sha
  until the planner answers; do not invent the ruling.

- **A test module that prints `N passed, 0 failed` locally can still be RED on CI `validate`: the repo's `test_workflows.py` hygiene rule fails any `test_*` DEFINED in a module but never CALLED from its `main()`.** A dead test never runs, so its green is invisible and its assertions do not execute — especially on a ported or freshly-created test file. Before trusting a local module run, confirm wiring: `python3 tests/test_workflows.py 2>&1 | grep 'every test_* in <module>.py is called from main'` must read `ok`, or grep the function names against the `main()` call list. Wiring the one missing call can jump the pass count sharply (previously-invisible assertions now run) — re-run the module after wiring to see the true count, then amend the single commit and re-push. This is exactly the CI red a local green masks; it is why "validate passed on my machine" is not a defense against the gate.
- **After a force-push, `gh pr view <n> --json headRefOid` can briefly return the OLD head while the new check-runs have already launched (GitHub lag).** Do not report or act on the first post-push view. Confirm the head landed by re-reading the PR once the checks show fresh run IDs (new job IDs / a new run id in `gh pr checks`), and trust that re-read over the first view. Reporting a stale head sha to the planner restarts a verify cycle against a sha that never existed on the remote.

## Additive-slice pitfalls (owner working default #690)

- New additive files are not enough: every staging seam must also keep the OLD path green.
  For the split store, `validate` gets additive checks that SKIP (not fail) when the new
  files are absent, so legacy stores and temp-dir make fixtures pass unchanged.
- When `main()` writes a new projection file (e.g. measurements/posts), temp-dir MAKE tests
  that copy only the old contracts into a fixture turn red: the fixture's own `_validate`
  hits the new checks. Copy the new contracts in `tests/test_make_commands.py::build_fixture`.
- A split→flatten refactor stays lossless only if identity is defined on NON-counter keys
  (engine/tps/hardware/quant/date/source_post/footprint); counters move to a once-per-post
  store and may only GROW (MAX across referencing rows), so a snapshot can never shrink.
- Commit-authorship guard is `python3 scripts/check_commit_authorship.py check` (needs the
  `check`/`report` subcommand arg). Branch must end `-<issue>` so `pr_closure.py` binds the
  `Closes #<issue>` line; run `scripts/pr_closure.py --branch <b> --body-file <f>` before
  opening the PR. Write the body file FIRST — `pr_closure.py` reads it eagerly and dies with
  `FileNotFoundError` when it is absent, and a `|| echo` fallback then silently reports success;
  re-run bare to read the real exit code.
- `make openspec-check` runs the OpenSpec CLI in Docker (`make openspec-new`/`validate`),
  so it needs a Docker-capable host; `scripts/openspec_index.py --write` +
  `check_openspec_tasks.py` run on the host python.
- Two host env tests fail even on the untouched base checkout: `test_openspec_archive_check`
  (the "missing gh" sub-test) and `test_worktree_base` (bot identity). They pass in the CI
  image. Never chase a green that the base itself does not have.
- `make lint` fails on any tracked file missing a trailing newline — including new OpenSpec
  change files and new test modules you just wrote. `write_file` does NOT append a final
  newline, so a file you author straight through the tool will trip this. **Run `make lint-fix`
  as the LAST step after every write, not earlier in the session** — a lint-fix run that predates
  a later `write_file` leaves the new file naked and the first CI run goes red on lint. Before
  committing, verify with `python3 scripts/lint_linefeeds.py` (it prints `OK every one of N
  tracked files ends with a newline`) and confirm the file you just touched is in the repaired
  list. When CI does go red on lint, the fix is one commit: `make lint-fix`, `git add` the
  repaired file only, commit, re-push — do not re-run the whole gate.
- When the planner flags a red gate, verify it against the CURRENT head's check-runs
  (`gh pr checks <n> --repo <owner>/<repo>` and `gh pr view <n> --json state,headRefOid`)
  before acting. The planner can cite an already-fixed, pre-re-push run (it did twice on #694,
  citing the original lint-failing run after the fix had gone green and the PR merged). Fix and
  re-push ONLY if the red is real on the exact current head; otherwise reply with the green
  head sha + merge sha rather than re-doing landed work.
- The CI `validate` job runs the whole suite inside Docker and takes ~18 minutes; `gh pr checks`
  will show it `pending` the entire time. To tell "still working" from "hung", poll the job and
  read its in-progress step: `gh api repos/<owner>/<repo>/actions/jobs/<job_id> --jq '.steps[] |
  select(.status=="in_progress") | .name'`. Keep waiting on a real step, not on the raw pending
  flag. **A `validate` that goes `fail` in under ~10s did not run the suite — it died at a fast
  gate (lint is the usual one).** Read the log instead of waiting a fix cycle:
  `gh api repos/<owner>/<repo>/actions/jobs/<job_id>/logs --allow-escape-sequences | sed
  's/\x1b\[[0-9;]*m//g' | grep -iE 'FAIL|error|Traceback'`.
- **Poll `validate` in bounded sub-timeout loops, never one long `sleep`.** The terminal tool's
  foreground timeout (~420s) is shorter than the job; `sleep 540` returns a tool timeout and you
  learn nothing. Loop instead: `for i in 1 2 3 4 5 6; do sleep 90; st=$(gh pr checks <n> --repo
  <o>/<r> | grep -E '^validate\s' | awk '{print $2}'); echo "check $i: validate=$st"; [ "$st"
  = pass ] || [ "$st" = fail ] && break; done`. Each `sleep 90` sits safely under the tool cap and
  the loop exits the moment the job settles.
- **Never concat a string and an object field in one `--jq` expression.** `'".state="+(.state)+"
  .merge="+(.mergeCommit)'` dies with `cannot add: string and object` because `mergeCommit` is an
  object, not a string. Access the sub-field (`+.mergeCommit.oid`) or use string interpolation
  (`"state=\(.state) merge=\(.mergeCommit.oid // \"-\")"`).

## Switch-over (catalog flip) pitfalls

- **A re-forwarded dispatch IS the ruling.** If you asked the planner for a scope choice and the
  reply refuses the question but says "go" again, stop blocking and implement what the dispatch
  commits to — escalate only when the acceptance criteria genuinely contradict each other.
- **A scope ruling that arrives AFTER the change already merged does not un-land it.** If the planner
  later prefers a narrower slice (e.g. seam+rewire, flip deferred) but the full delivery is already
  MERGED and green and the issue auto-closed, do not reopen the closed issue and do not un-merge a
  verified lossless change to shrink scope. Verify the LIVE state from GitHub (merge commit, head sha,
  issue closedAt), answer the technical blocking question with measured evidence (see the flat-vs-flat
  probe above), and recommend reviewing the combined delivery as the single switch-over it was titled
  for — it is lossless and every gate was green on its head. Resplit only on an explicit NEW dispatch
  from `tll-planner` against current `origin/master`, filed as a fresh follow-up path.
- **A `tll-planner` instruction to "re-push PR #N with these fixes" is NOT executable when #N is
  already MERGED — pushing to that branch lands on `master`.** Always check first:
  `gh pr view <n> --repo <o>/<r> --json state,mergeCommit,headRefOid`. If `state=MERGED`, the
  correct move is a NEW worktree from the freshly fetched `origin/master`, a new
  `fix/<slug>-<fix-issue>` branch, and a NEW PR whose title AND body carry `Closes #<fix-issue>`
  (the follow-up issue the reviewer/tester filed for the defect). Do not reopen the merged PR and
  do not force-push a merged branch. Tell the planner its queue is stale and name the new PR. One
  merged PR closing the switch-over issue, a separate follow-up PR closing the defect issue — never
  fold the defect fix back into a merged PR.
- **A no-value-loss / additive guard proves monotonicity, not correctness — when a change
  RE-RESOLVES a field from a canonical source, pair it with a value-for-value equality test**
  against that source. `check_no_value_loss` only says nothing shrank; it passes even when a reader
  silently switches to different numbers (the exact `trend`/`buzz` re-resolution the reviewer will
  flag). Add a test that iterates every row `flatten_store` resolves and asserts each counter equals
  `posts[source_post]` value-for-value, with a row that has no canonical post entry asserting 0 (not
  skipped — that path is where a silent zero-regression hides). "Non-shrink" and "equals the source"
  are two different GWT claims; when the semantics changed, merge needs both.
- **If a reviewer proves an OpenSpec claim in your own MERGED change is false, concede in one line
  and fix the claim text in the fix PR — do not defend the old wording.** The artifact is the WHOLE
  change dir under `openspec/changes/<slug>/`, i.e. **all three** files: the proposal bullet, the spec
  scenario title, AND the ticked task lines in `tasks.md`. `make openspec-check` validates only that
  task boxes are TICKED, never what they say, so a false sentence in `tasks.md` passes the gate and
  ships to master silently while the proposal reads correct. After correcting, grep the change dir for
  the exact false phrase (`grep -rn '<phrase>' openspec/changes/<slug>/`) and confirm every remaining
  hit is the corrected "not claimed X" wording — a hit is the uncorrected claim, not a mention. Retitle
  the spec scenario to what actually happens (e.g. "engagement-derived buzz/trend lines re-resolve from
  the canonical posts store, README regenerated accordingly"), and ship that corrected text alongside
  the guard. Arguing the technical point, or fixing only some of the three files, is not a fix — and
  the issue may already have auto-closed `COMPLETED`, which is why the re-read below matters.
- **The flip only breaks readers that load the file from disk.** Code that already receives a
  store object is fine; the blast radius is exactly `json.load(...)`/`load(STORE)` call sites in
  scripts and tests. Enumerate them first: `grep -rn 'models.json' scripts/ tests/ | grep -v load_store`.
- **Migrate them mechanically to the one seam** — `UT.load_store()` from `scripts/update_trending.py`
  (it flattens only when the split files exist, else returns the store unchanged, so self-built
  flat fixtures stay green). A reader script that cannot import that module gets a local
  `_load_flat_store()` helper doing the same.
- **Tests that copy the shipped file into a temp dir need the split files copied too**, or
  `load_store()` falls back to the bare catalog and the render/check path sees no engines.
- **Recompute stored engagement after the flip**, then regenerate the README from the flattened
  view. The flatten legitimately raises shared-post counters (counters only grow), so a README
  that still matches the pre-flip byte-for-byte means the render never saw the split store.
- **"Different buzz numbers vs the old README" is the blocking question a reviewer asks — answer it
  with a measured flat-vs-flat probe, not prose.** Run `scripts/verify-flatten-no-loss.py` (from the
  repo root): it compares the NEW flattened view against the OLD inline view (the newest pre-switch
  snapshot under `data/snapshots/`, which IS the old inline store) and prints three numbers. Healthy/
  designed re-resolution is `tps_field_changed: 0`, `counters: grew N, shrunk 0`, `additive keys`
  only. Any `shrunk` counter, moved t/s, or gone valued field is a REAL loss — stop and fix. Map the
  answer explicitly: t/s bands + ranking byte-identical (the 'flattened == old inline' GWT is scoped
  to these), while buzz is re-resolved from the canonical posts store (a designed, more-correct
  number). Quote the grew/shrunk counts and the zero-t/s-change proof in the issue comment; a "loss"
  would show shrunk counters, and there are none.
- **Do not compare the flattened view against `UT.load_store()`** — `load_store()` already returns the
  flattened view, so that diff is tautological (it prints `grew 0 shrunk 0` and proves nothing). The
  only honest oracle is the newest pre-switch snapshot file. Likewise do not build a band key by
  `str(e.get(k))` over optional footprint fields: a missing optional key becomes `'None'` on one side
  and a real value on the other, producing phantom "lost bands" that are actually additive keys.
  Match bands by engine+hardware identity and diff fields individually (the script already does).
- **Suffix "Landed" with the merge state — "Landed" without a merge status reads as "merged to master".**
  The planner greps `origin/master` (e.g. `git grep test_flatten... master`) as its source of truth, so a
  delivered-but-UNMERGED PR (CI pending, `qa-validate` not yet green) will verify as "absent" and keep
  producing a stale "not started" re-dispatch loop no matter how many DMs you send. Say explicitly
  "delivered as PR #N, state=OPEN, head <sha>, CI <pending/pass>", cite the live `gh pr view` + `gh pr
  checks`, and name the branch. If the issue needs a correction item that lands separately, do not rest
  until BOTH the guard PR and the claim/text PR have merged to master — a single merged PR with the claim
  text still wrong in `tasks.md` leaves the defect shipped (openspec-check only checks tasks are ticked).
  Re-read the whole change dir on `origin/master` after EACH merge, not after the first one.
- **Planner DM replies that arrive as background results can be STALE** — they are queued from the
  planner's bot run and may predate the answer you already posted. When two or more land and each re-asks
  a question you already answered with evidence, do NOT re-send (that is ping-pong): verify against the
  live GitHub record (the issue comment you posted, the PR head/merge state), state the delivery is
  stale/superseded, and hold. The durable issue comment is the record the planner actually reads; repeat
  only genuinely NEW asks.
- **A planner that says "my PR is OPEN, stand by for CI" can be stuck on a pre-merge snapshot for many
  turns — settle it with `state` + `mergedAt`, not with argument.** The discriminator is
  `gh pr view <n> --json state,mergedAt,mergeCommit`: `state=MERGED` with a non-null `mergedAt` means the
  gate already ran (never self-merged — `qa-validate` closed it on green) and there is nothing to "stand
  by" for; a queued dispatch insisting otherwise is stale, not a new instruction. Pair it with
  `git ls-remote origin master` (prints the full live head sha) so the reply names master's real sha, and
  answer ONCE with that evidence on the issue plus a DM, then hold — re-explaining on every queued
  arrival feeds the loop instead of ending it. If the planner then claims a mid-merge ordering
  (`04ad45c -> dd367af -> 3847be7`), quote the two merge commits rather than re-running verification
  cycles.
- **When a reviewer says "point to the specific test", answer with the GWT→test-function map and quote
  line ranges** from `tests/test_measurements_split.py`: `test_catalog_has_no_inline_engines` (GWT1),
  `test_engagement_resolved_once_from_posts` (GWT2 re-resolution — each row's counters == the ONE
  `posts[source_post]` entry), `test_flatten_equals_old_inline_guarded` (GWT3 — `check_split_flatten` +
  `check_no_value_loss` green), `test_renderer_materialises_same_ranking` (GWT4 — render via the flattened
  view, `best_measurement` + `tier_trending_rows`), `test_support_surface_reads_same_store` (GWT5/#338).
  Naming the function + lines is the answer to a "designed vs regression" challenge — not prose.
- Never `git stash` inside a fresh worktree to "save" experimental state — the pop can resurrect
  an unrelated old stash from another branch and fill the tree with conflict markers. Delete and
  re-write the file instead.

## Data-fix pitfalls (`data/models.json`, attribution / dedupe / value-loss)

Full recipe in `references/data-fix-hygiene.md`. Always-on rules:

- **Removing a row is not "delete the line".** After any row edit, re-run the pipeline's own
  sort/engagement recompute **as-of the store's existing `generated_utc`** (do not re-stamp the
  timestamp). The stored engagement fields otherwise diverge from the freshly rendered README and
  `validate` fails on the mismatch — the renderer recomputes on sort, the store file still holds
  pre-edit values.
- **`check_no_value_loss` is additive-only against the newest snapshot.** Deleting rows shrinks the
  store, so you must append **one corrected snapshot** so the corrected baseline is what the next
  run compares against. Without it the removal reads as loss.
- **Define a duplicate by the full measured tuple `(engine, tps, hardware, source_post)`, not by
  the one row the issue names.** A value copied onto a second model ID appears as one post measured
  on two models. Scan the whole store and make the allow-list explicit (same-family variant IDs,
  and posts that genuinely measured both models) so a *new* copy is loud, never silent.
- **Express the fix against the CURRENT store shape, not the shape it was authored on.** After the
  catalog flip, measurement rows live in `data/measurements.json` (engagement in `data/posts.json`)
  and `data/models.json` is catalog-only. Re-derive the fix through the pipeline seams —
  `load_store()` → edit the flat view → `split_store()` — so `check_split_flatten` (split files ==
  `split_store(flatten_store(...))`) stays green. Hand-editing the old flat file re-introduces the
  shape the flip removed.
- **Never feed the raw catalog to `split_store()`.** It expects the flat store with `engines[]`; hand
  it `data/models.json` as it sits after the flip and it emits near-empty `measurements.json`,
  silently corrupting the split data (`check_split_flatten` then fails on ~578 missing rows). Always
  pass `load_store()`/`flatten_store()` output into `split_store()`.
- **Preserve the committed `models[]` array order; let only the rows you fixed differ.** Re-running
  `sort_models` reorders every model even when no value changed — unrelated churn a reviewer flags
  against the #690 no-churn rule. `render_readme` re-sorts internally so the on-disk array order does
  NOT affect the README; keep master's order for untouched models and prove it with `git diff`: only
  the affected model IDs appear (seen_posts removed, engagement recomputed), none moved. Confirm the
  measurement-file diff is exactly your intended removals with **zero added** rows (`removed==N`,
  `added==0`) by diffing entries by identity, not line count.
- **An attribution test asserting "the copied post disappears entirely" is too broad** — the poster
  can legitimately reappear via a different model/engine it also measured (a shared post measured on
  two models). Tighten the assertion to "the copied model ID no longer shares the duplicate tuple",
  never "the source post vanishes from the whole scan"; the broad form is the red the gate catches.
- **Render-only, as-of `generated_utc`.** `scripts/update_trending.py --render-only --dry-run`
  must be byte-identical to the committed README (a trailing blank line from `print()` is a
  `--dry-run` artifact, not drift). The real byte-for-byte gate is `check_readme_generated`.
- **A huge diffstat on a data PR is usually the full-store snapshot**, not a runaway renderer.
  Run `git show --stat` before suspecting the edit — ~19K insertions is one snapshot dump.
- **Regenerate the OpenSpec index after adding a change dir** (`scripts/openspec_index.py --write`)
  or `make openspec-check` fails on a stale `OPENSPEC.md`; and grep the test tree for the name in
  the spec's `- **Test:**` line before running the gate — the gate fails on a test that is absent.
