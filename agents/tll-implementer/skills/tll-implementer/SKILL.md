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
- **A change dir authored BY HAND (not via `make openspec-new`) lacks `.openspec.yaml`; add it (`schema: spec-driven` + `created: <YYYY-MM-DD>`) so the dir matches every sibling.** Measured on #1442/PR #1628: `make openspec-new` normally writes it, and `openspec/changes/archive/*/` shows it in every archived dir, so a manual dir is the odd one out.

## Testing convention (owner-mandated, issue #690)

- Every PR ships CLEAR OpenSpec acceptance criteria AND Python unit tests that exercise the REAL business logic — e.g. for #689, tests in test_measurements_split.py call the real flatten/render/rank/store functions on real fixtures. Tests-only-mocking-logic is a defect.
- NEVER mock the business logic. Mock ONLY the main pipeline's external calls (network, filesystem I/O, subprocess, remote registry) where a test cannot run the real call.
- Wherever the main pipeline uses a mock for an external call, an END-TO-END pipeline test MUST run the real business call input-to-result (no mock) — keeps data-sync honesty intact. A PR that mocks the pipeline without an E2E real-call test is NOT done.
- Coordinate with `@tll-tester` (test lane): it tests my PR against the issue's acceptance criteria, running the real unit + E2E tests, and the PR must be green on its evidence before the gate merges.
- For #689 when the architect's design lands: my write PR must include that change's OpenSpec files and pass the gate on the PR head.

## Working default (owner-mandated, issue #690)

Work in **worktrees** branched from the **latest fetched `origin/master`**. Never edit the owner's checkout at `/home/asimov/repository/git/trending-local-llms`. Branch only in your worktree, never push to `master`; `qa-validate` merges. No Hermes cron and no new GitHub Actions schedule. This convention is captured in issue #690 and overrides any older procedure text below.

## Delivery procedure — push, then CI verifies (owner directive 2026-11-23, issue #1423)

Make the change in the worktree, run ONLY the fast offline checks, **PUSH**, then confirm CI registered on
the new SHA and report. Never pre-run the full containerised suite on the host.

Fast offline checks — seconds each, no network:

- `python3 scripts/pr_body.py --check-body-file <f> --branch <b>` — the body's five sections and its closure binding.
- `make lint` — trailing newline on every tracked text file, no `SyntaxWarning`, bot skill + model chain present.
- the targeted unit module for the change (`python3 tests/test_<module>.py`), never the whole suite.

Then PUSH, and confirm CI registered on the new SHA:

- `gh pr checks <n>` and `gh run view <id> --json jobs`. A head with NO jobs is a never-started run, not a green one.

**CI-ONLY — do NOT run these locally:** the full `make validate`, the whole `make test`, and
`make live-smoke`. They run in GitHub Actions on `qa-validate` and cost this host nothing. Measured
locally they take 15–30 min each inside the per-purpose Linux container, and N lanes running them at
once contend for ONE VM (load 5.80, `Virtualization.framework` at 207% CPU) while each lane process
sits at ~0% CPU in `sleep` polls.

## Standing rules (owner-mandated, issue #703) — bind every task

1. **Fetch latest first.** Before ANY measure, claim, or branch cut run `git fetch origin master` and base work on the `origin/master` sha fetched in that moment — never a sha quoted in chat (stale). Record the sha you measured.
2. **Worktree only.** Start new work from a worktree created from the latest fetched `origin/master`, never the owner checkout at `/home/asimov/repository/git/trending-local-llms`, and never push to `master`.
3. **CLAIM / READ / REPORT.** (a) CLAIM: post the signed working-claim comment on the issue BEFORE starting — `BOT tll-implementer · working on #<id> · branch <ref|none> · blocked on <x|none> · next <y>` on the issue's OWN thread. No silent pickups. (b) READ: read the issue thread FIRST to check whether ANOTHER lane already holds a live working-claim on the SAME issue. (c) If a collision exists, do NOT start — REPORT it to `tll-planner` on that same thread and await re-dispatch. Never two bots on one issue. (d) REPORT: finish with a signed record of what you changed on the issue.

## Concurrent-lane contract (issue #1767)

These obligations bind EVERY `tll-implementer` lane whenever the fleet runs in parallel. They add to, and do not replace, the claim, worktree, push-and-verify and handover rules in this skill.

- **One issue, one worktree, one branch per lane.** A lane owns exactly one issue, works it in its own worktree cut from the freshly fetched `origin/master`, and pushes only its own branch. Two lanes never work the same issue, share a branch, or edit the same file.
- **Signed claim before work.** Post `BOT tll-implementer · working on #<id> · branch <ref|none> · blocked on <x|none> · next <y>` on the issue's OWN thread before starting, and re-read that thread for a newer claim before you write.
- **No shared branch or file edits.** Never edit another lane's branch, worktree or files, and never amend, rebase or force-push a branch you did not claim. Overlapping file claims mean stop and hand over to `tll-planner`.
- **At most 3 live implementer lanes.** Up to three lanes run concurrently, each on a distinct issue and a distinct file set; a fourth waits for a board-visible `pr`/`done` bookend from a lane that finished.
- **Lease-checked push.** Push with `--force-with-lease` against the sha you last read from `origin/<branch>`; a rejected lease means re-read, rebase YOUR OWN branch and re-push, never overwrite a sibling's commit.
- **No master push, no merge.** Never push to `master`, never run `gh pr merge`, never approve your own pull request; `qa-validate` merges green heads.
- **Every lane loads its own SOUL.md and SKILL.md.** Before claiming, each lane reads its own profile's `SOUL.md` and skill `SKILL.md` — and the dispatched versions when the host is ahead — and follows their obligations even while other lanes run concurrently.

## Procedure

1. Do not create a cron job. If `cron/jobs.json` exists, stop and tell the owner. This fleet does not run on a timer.
2. Read `SOUL.md` in this profile. The repo is https://github.com/andyholst/trending-local-llms, branch `master`.
3. READ the issue thread FIRST: confirm no other lane holds a live working-claim on the same issue. On a collision, do NOT start — report to `tll-planner` on that thread and await re-dispatch.
4. CLAIM before starting: post `BOT tll-implementer · working on #<id> · branch <ref|none> · blocked on <x|none> · next <y>` on the issue's OWN thread.
5. Fetch before you measure: `git fetch origin master` in a worktree that is not `/home/asimov/repository/git/trending-local-llms`. Record the sha. A sha from chat is stale.
6. Make the change in the worktree, run ONLY the fast offline checks (`python3 scripts/pr_body.py --check-body-file <f> --branch <b>`, `make lint`, the targeted unit module), PUSH, and confirm CI registered on the new SHA (`gh pr checks <n>`, `gh run view <id> --json jobs`). Full `make validate`, the whole `make test` and `make live-smoke` are CI-ONLY — never pre-run them locally. See `## Delivery procedure`.
6. Do the lane work in `SOUL.md` and stop. Coordination lanes file or comment. Only `tll-implementer` writes the tree, and only after the planner names the issue.
7. RED-first: every acceptance criterion the change adds is locked by a test that FAILS on `git show origin/master:<product-file>` and PASSES on the fixed head. RED-verify in a scratch tree cut at the fetched base with the new test overlaid, then a driver that imports only the new test functions, and run it against BOTH heads before committing. A test that cannot fail on the old code proves nothing; a local green that cannot fail on the base is a dead test (see the `test_*` never called from `main()` pitfall).
8. Post the result on the issue. The comment is the record.

## This lane

- Wait for a `tll-planner` comment that names this profile, the issue, and the `origin/master` sha. Fetch that sha and branch in a fresh worktree. Do not use the checkout at `/home/asimov/repository/git/trending-local-llms`.
- One issue, one branch, one pull request. The branch ends in `-<issue number>` so `scripts/pr_closure.py` binds it. The body has its own `Closes #<issue>` line and no second closing reference on that line.
- The PR **title** carries the change and `Closes #<id>`; the **body** repeats its own `Closes #<id>` line — both-required, never title-only or body-only (owner-mandated; #682 stayed open after PR #688 merged even with a proper body).
- **Open every PR READY (never draft) — owner directive 2026-11-24.** Every fleet PR goes up ready for review. A draft is invisible to reviewers and to `auto-merge` (verdict `draft` → "untouched"), so it silently stalls the board and hides finished work. Write the complete five-section body with `Closes #<id>` in both title and body, run the fast offline checks, and open the PR ready — never with `--draft`. If the work is genuinely unfinished, report status on the issue instead of opening a PR. `make pr-draft-check` names a bound draft PR with its issue.
- Commits are authored `Andy Holst <andy.holst@protonmail.com>`. Open the pull request ready for review. `qa-validate` merges it when `validate` and `live-smoke` are green. Read the state back, comment the head sha, and then verify the referenced issue actually went closed on GitHub — a merge that leaves the issue open is a defect to fix with a record comment naming the PR, sha and merge time.
- Copy the lane soul and skill you were dispatched to version into `agents/<profile>/` so the repo matches the host profile.

- You do not start because an issue exists. You start because the planner dispatched it.
- You do not run `gh pr merge`, do not approve your own pull request, and do not push to `master`.
- You do not add a Hermes cron or a GitHub Actions schedule. You do not label the issue `tech-debt` or `data-gap-analysis`.
- A red pull request is yours only when `tll-planner` names it in a comment. You do not pick one up on your own.

## Pitfalls

- **Land a design's PINNED COUNTS only after RE-MEASURING them on the CURRENT base.** Measured on #1675: the design (`7148545848`) was authored on `e93bc67d`, but #1679 had since moved `scripts/gh_json_fields.py`; the dispatch said re-anchor by content, so re-count the sites on the fetched base (31 discovered token-lists / 17 projecting / 14 none, + the `GH_API` splat = 32 read sites, 18 Python field reads) and confirm the number is unchanged BEFORE shipping the verbatim text. Equal here — but a drifted count would have shipped a stale number under a "verbatim" label.
- **A branch name starting `docs/` is EXEMPT from `make findings-check-for-pr`** (`[findings] SKIP <branch>: exempt shape (docs/)`). That skip is not permission to omit the record: when the dispatch names `findings/<issue>.md`, still ship it and verify it by hand (`python3 scripts/file_findings.py --check --branch <b> --body-file <f>`), because CI will not check it.
- A Hermes cron or a new GitHub Actions `schedule:` is the wrong tool. The owner asks on the host. The data sync is the existing weekly refresh, not a new timer.
- `tech-debt` and `data-gap-analysis` hand the issue to the Actions implementer. This fleet uses `enhancement`.
- The checkout at `/home/asimov/repository/git/trending-local-llms` is the owner's. Do not edit it.
- **A "behavior lift" dispatch that edits your own host `SOUL.md` + skill is a HOST edit (direct, no branch, no PR) — but the in-tree `agents/<profile>/` mirror is a SEPARATE shared TREE WRITE that belongs to its own mirror-refresh PR, never folded into an active issue branch.** When such a dispatch also says "sync the mirror", first determine whether the mirror refresh is a queued multi-lane tree-write (it usually is — the refresh adds/updates several lanes' copies and is dispatched once). If so, prepare the content but keep it OFF any active issue branch (never fold issue N's mirror into issue M's PR) and ask the planner when the mirror PR should be cut rather than opening a partial single-lane PR that jumps the queue. Confirm the committed mirror is actually stale before copying — `git show HEAD:agents/<profile>/SOUL.md | grep -c 'Standing rules'` returning 0 means the in-tree copy predates the host rules and must be re-synced from current host content. Stage the copy, then `git checkout -- agents/` to keep it off the branch you are resting. **Byte-match a mirror against its source with the final newline NORMALIZED, never a raw `cmp`:** `write_file` does not append a trailing newline but the repo's `make lint` requires one, so a correctly-synced file that differs from host by exactly one final-newline byte is content-identical, not drift. Compare with `diff <(sed -e '$a\' hostfile) <(sed -e '$a\' mirrorfile)` (or strip both then `cmp`) and report "BYTE-MATCH (modulo lint newline)"; a raw `cmp` that flags only the last byte is a false alarm that sends you re-copying a file that was already right.
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
- **Never write scratch/PR-body/record draft files into the worktree tree — a `.prN.md` / `.recN.md` / any dotfile-at-root gets swept into the commit by `git add -A` and ships as dead, unreferenced code that the reviewer flags under the #690 clean-code lens.** Author the PR-body and issue-comment text in the profile scratch dir (`$TMPDIR`) and `--body-file` that path, never a file inside the branch worktree. If one does leak in, strip it via `--amend` (deletion must be STAGED, not just `rm`'d) and prove the tree is clean BEFORE re-pushing: `git rm --cached <f>; git rm <f>` then `git status --short` must show `D ` in the INDEX column (leading `D`), and `git ls-tree -r --name-only HEAD | grep -E '\.(pr|rec)[0-9]'` must print nothing. **A bare `git add <deleted-file>` after `rm` does NOT stage the removal (`git status` shows ` D` = unstaged) and `commit --amend --no-edit` then re-commits the tree WITH the file still in it — the amend silently 'succeeds' and the file survives to the pushed head.** Verify the PUSHED head's tree (`git ls-tree -r --name-only <head> | grep <f>`), not just the worktree, then re-push with `git push --force-with-lease origin HEAD:<branch>`.
- **`validate`'s merge-tree index check can red on a branch whose base is NOT behind master** — measured on #1583/PR #1590: the first head `1df39821` had been cut from the then-current master and the rebase onto the advanced master was CLEAN (no conflicts), yet `OpenSpec index on the merge tree` still went red because master's own `OPENSPEC.md` edits landed after the fork. Never read that red as "rebase and hope": after rebasing, ALWAYS run `python3 scripts/openspec_index.py --write` (not just `--check`) so the regenerated file matches the merged tree, confirm `scripts/openspec_archive_check.py --pr <n>` still says no active change left unarchived (the record-pr/archive step survives the rebase, but re-verify), then force-push with an explicit lease.
- **After a force-push, `gh pr view <n> --json headRefOid` can briefly return the OLD head while the new check-runs have already launched (GitHub lag).** Do not report or act on the first post-push view. Confirm the head landed by re-reading the PR once the checks show fresh run IDs (new job IDs / a new run id in `gh pr checks`), and trust that re-read over the first view. Reporting a stale head sha to the planner restarts a verify cycle against a sha that never existed on the remote.
- **A PR body missing `## Technical Solution` is a fast red in the `closure` job, not a warning.**
  `scripts/pr_body.py` requires all five sections (`Why`, `What`, `How`, `Benefits`,
  `Technical Solution`) and `make pr-message-check` refuses the PR in seconds. Author the body with
  ALL five from the start; `make pr-closure` does NOT check this (it reads the closing bindings only),
  so a `pr_closure.py` OK is not a green closure job. Run
  `python3 scripts/pr_body.py --check-body-file <f> --branch <b>` before opening the PR.
- **A `git rebase --continue` can ship a commit whose MESSAGE lost your `--amend` edits — re-read and
  re-check the message on the rebased head before every push.** Measured on #1427/PR #1429: the
  branch commit carried all five `##` sections (`pr_body.py --check-commit-file` OK), the rebase onto
  an advanced master conflicted, and after resolving + `GIT_EDITOR=true git rebase --continue` the
  resulting commit had NO `## ` sections — so `--check-commit-file` REFUSED again and the `closure`
  job would have reddened on a head I had already pushed. Do not trust that an amend survived a
  rebase: run `git log -1 --format=%B | grep -c '^## '` and `python3 scripts/pr_body.py
  --check-commit-file <(git log -1 --format=%B) --branch <b> --issue <id>` on the NEW head, and
  `--amend` again if the count is short. Related: a rebase that touches `OPENSPEC.md` can also leave
  the count line one row behind master's own archive — regenerate (`scripts/openspec_index.py
  --write`) rather than hand-editing the collision.
- **`git commit -F <file>` STRIPS every line starting with `#` (default cleanup treats `#` as a comment
  char), so a five-section message silently ships with NO `## ` headers.** Measured on #1445: the body
  file was correct but `git log -1 --format=%B | grep -c '^## '` returned 0 and `--check-commit-file`
  refused after the commit. Use `--cleanup=verbatim` on both the commit and any `--amend --no-edit`, then
  re-grep `^## ` = 5 BEFORE pushing; a rebase `--continue` can also drop them, so re-check after it too.
- **RE-READ the issue thread IMMEDIATELY before you push or open the PR — the race-guard re-read at claim
  time does not cover the whole work window.** Measured on #1445: `tll-planner` posted a SEQUENCING
  ruling at 17:51:27Z ("wait for PR #1448 to merge; land ONLY the residual delta") 17 seconds before my
  PR comment; I opened PR #1449 anyway, it merged first, duplicated #1448's notes and left #1448
  CONFLICTING. If a ruling lands mid-work, stop and obey it — a competing PR that jumps the queue costs
  the planner a reconciliation and the board a conflicting PR.
- **`validate` runs an OpenSpec index check on the MERGE TREE (`git merge --no-commit --no-ff origin/master`
  + `make openspec-index-check`, issue #1239), so a green index on YOUR head is not enough.** Any PR that
  adds/archives an OpenSpec change races master's own index edits and reds with
  `[merge-tree-index] MERGE CONFLICT` or `FAIL: the index is stale on master + this PR` after ~13 min.
  Remedy: rebase onto the freshly fetched `origin/master`, resolve the `OPENSPEC.md` conflicts (the
  `Active changes: **N** · archived: **M**` count line is the usual collision), run
  `make openspec-index`, commit, re-push. Prove it locally first with the same merge + index check.
- **Before routing a `python3 scripts/…` make target through `$(PYTHON_RUN)`, MEASURE which existing
  tests execute it through `make`: `make test` runs the whole suite INSIDE the docker-less test image,
  so a docker-routed recipe invoked by `subprocess.run(["make", "<target>", …])` dies with
  `FileNotFoundError: 'docker'` at the `python-env-image` prerequisite.** Measured on #1399: routing
  `pr-title`/`pr-body`/`architecture-pr-body` red 21 in-container checks across `test_pr_body.py` (15),
  `test_workflows.py` (4, via the executed "Open the PR" step) and `test_architecture_bot.py` (2, via
  `make keeper-pr` -> `make architecture-pr-body`). A target is landable only if no test drives it
  through `make` (the three keeper `*-pr-body` targets were; the composer batch was split to #1411).
  Also check HARD for paths/env the container drops: `gh` calls, `WINDOW_FILE`/`LEDGER` host paths, and
  values read with `os.environ.get(...)` (e.g. `RUN_URL`) — `PYTHON_RUN` forwards none of them.
- **The merge-tree index race is PER-MASTER-MOVE, so expect several rebase cycles, and `auto-merge`
  can fail with `not mergeable` even after `validate` + `live-smoke` are green.** Measured on #1432/PR
  #1434: master advanced four times inside one PR's lifetime (`0c8d3f6c -> d792d29f -> 93b67ca5 ->
  213df431 -> 07bcb204`), each landing `OPENSPEC.md`; `validate` went green on the rebased head every
  time, but the squash step then found the merge commit uncleanable because master had moved again
  between the validate run and the merge. Each cycle: fetch, rebase onto the new `origin/master`,
  resolve EVERY conflict — not just `OPENSPEC.md` (a concurrently-landed `tests/test_fleet_lifecycle.py`
  edit conflicts inside the `main()` call list; keep BOTH sides' entries, do not take one side whole),
  regenerate the index, re-run the merge-tree simulation, force-push. Tell a master-move race from a
  real red by reading the failing step:
  `gh run view <id> --log-failed | grep -iE 'not mergeable|master ->|MERGE CONFLICT'`.
- **A sibling rulebook PR can make `AGENTS.md` conflict too, not just `OPENSPEC.md` — resolve the §7b `Rule 3c note` as a UNION, never by taking one side.** Measured on #1482/PR #1597: master's #1589 had appended its own provenance clause to the SAME `Rule 3c note` line my approved `#1395` clause appends to, so the rebase conflicted in `AGENTS.md` as well. Take master's whole line and append YOUR clause LAST (a guard test often asserts `endswith(<your clause>)`), then prove `git diff origin/master -- AGENTS.md` is still exactly your approved edits. Same for any other shared appended clause/row: keep both sides' entries, regenerate `OPENSPEC.md` with `scripts/openspec_index.py --write` at EVERY hop of the rebase (the second commit re-conflicts), and re-run the message-pattern check on the final head.
- **Carry reviewer-approved verbatim texts as constants in the guard test, and re-extract the approval from the issuecomment before writing.** Fetch the signed comment body (`gh api repos/<o>/<r>/issues/comments/<id> -q .body`), pull its fenced blocks, and string-compare them against the constants; apply the texts FROM those constants. This makes "land it verbatim, do not improvise" mechanically checkable instead of a copy-paste hope.
- **The `validate` job also runs the OpenSpec LIFECYCLE gate (`make openspec-archive-check PR=<n>`): a PR
  whose branch closes issue N may not leave N's OpenSpec change ACTIVE, or validate reds AFTER a green
  lint/openspec/index/merge-tree run (~12 min in) with `THIS PR #<n> closes issue #N while the change is
  still ACTIVE`.** Remedy: create the PR first, then on the branch run
  `make openspec-record-pr ISSUE=<n> PR=<pr>` — it writes the `PR:` line, ARCHIVES the change and
  regenerates `OPENSPEC.md` (e.g. `1 active, 456 archived`) — then stage everything (`git add -A`),
  `commit --amend --no-edit` and `push --force-with-lease`. Verify with
  `python3 scripts/openspec_archive_check.py --pr <pr>` (prints `no active change left unarchived`)
  BEFORE waiting on CI; doing this only after seeing the red costs a full validate cycle (#866, #1434).
- **Never run `git reset --hard` (or `git checkout -- <file>`) AFTER regenerating a generated artifact
  and BEFORE staging it — the cleanup silently reverts the regeneration, and the amend/push then ships
  the STALE file behind a green local check.** Measured on #1423/PR #1424: regenerated `OPENSPEC.md`
  (`1 active, 461 archived`), proved `scripts/openspec_index.py --check` OK, then ran a local merge-tree
  simulation whose cleanup ended with `git reset --hard HEAD`; the next `git add OPENSPEC.md` staged
  nothing, `--amend --no-edit` kept the stale `459` count line, and CI red'd
  `[openspec-index] FAIL ... the count line says 'archived: **459**', disk needs '**461**'` — a full
  ~13 min validate cycle wasted on a file I had already fixed. Order the steps: destructive cleanup
  FIRST (`git merge --abort` alone is enough for a trial merge), THEN regenerate, THEN stage; and
  before reporting, confirm the PUSHED tree, not the worktree —
  `git show origin/<branch>:OPENSPEC.md | grep 'Active changes:'` must equal
  `ls openspec/changes/archive | wc -l`.
- **`test_engine_registry.py` is RED in a local test-image run WITHOUT `GH_TOKEN`** (the metadata probe
  leaves a date-driven repeat WARN like `StairCut` unresolved, so `engine-check exits 0` fails). CI
  forwards `GH_TOKEN` and master's own runs are green, so this is a local-environment artifact, not a
  regression — prove it by running the module against pristine `origin/master` in the same image before
  chasing it (#972).
- **A PR can register ZERO `pull_request` workflow runs after a force-push AND a body edit, while
  master-push runs keep arriving — post the honest "no CI registered, not green" record and stop,
  do not churn the branch with repeated empty retrigger commits.** Measured on #1593/PR #1566:
  two `--force-with-lease` pushes and a `gh pr edit` body change over ~8 minutes produced no
  `qa-validate` / `pr-closure` run for the new head (check-runs endpoint empty, the PR's check
  list said "no checks reported"), yet master-push runs registered normally minutes later. One
  documented owner-identity empty retrigger commit also failed to register a run; further pushes
  are churn. Report the exact head, the evidence (run IDs / timestamps), and hand over — never
  describe a no-job head as green, and never invent a verdict.
- **A lane can force-push YOUR branch between your push and the merge; re-read the head before
  reporting a verdict.** Measured on #1398/PR #1406: another lane rebased my head to a new sha, and the
  new head's qa-validate ended `action_required` with ZERO jobs (the #1115 never-started shape), so the
  old head's green no longer described the PR. Check `gh pr view <n> --json headRefOid` against the sha
  you measured, and treat a 0-job `action_required` as a head to RECOVER on your own branch (owner-identity
  empty commit + `--force-with-lease`, then `gh run view <id> --json jobs` shows the new run has jobs),
  never as a red gate to re-fix.
- **A lane's `--yolo --accept-hooks` protects it from shell/hook prompts, NOT from
  `approvals.single_query_mode: deny` on a privileged git write — pass both flags when a dispatch tells
  you to start another lane.** Also: a lane's shell cwd is not automatically its worktree, so check the
  owner's checkout with `git status` after a lane run; a lane runs 30–70 min, so monitor it with
  `process_manage` rather than assuming it finished.
- **The master-alarm routing sees only a BARE `make <target>` LINE** — `scripts/master_alarm.py::job_gate_map`
  uses `make\s+([a-z0-9_-]+)(?=["'\s]|$)`, so `make -C <dir> X`, `if ! make X; then` and
  `$(PYTHON_RUN) make X` are all INVISIBLE to "which gates does this job run", while
  `validate_gates_from_trees` (the whole-file read that catches an unregistered gate) DOES see them. A
  gate written inside an `if ! make X;` therefore reds `tests/test_master_alarm.py` (`uncovered=['X']`)
  even though the step plainly runs it. Write CI gate calls as a bare `make <target>` line and read `$?`
  for a named failure branch — and register every real make target a job runs (`make python-env-image`
  is a REAL target, not a no-op, so it needs a `GATES` row too). Note the two readers differ:
  `_wf_text()` slices the `validate:` job, `unchecked_gates()` reads the whole file.
- **Before writing any code on a dispatch, re-read the PR's live state — it may already be MERGED and the
  issue CLOSED by another lane while you worked.** `gh pr view <n> --json state,mergedAt,mergeCommit` +
  `gh issue view <id> --json state,closedAt` is cheap and settles it; a planner dispatch naming an old
  base sha does not mean the work is still open. When the PR already merged as master `<sha>` and the
  issue is CLOSED, do NOT open a second competing PR for the same issue (one issue, one branch, one PR)
  and do NOT force-push a dead branch — verify the SHIPPED artifact on `origin/master` against every
  acceptance item (`git show origin/master:<path>`, run the real step shell on a fixture), then post the
  signed record with that evidence and hand over. A redundant variant is churn the reviewer has to
  untangle.
- **The claim-twice window (~80 s) is SHORT enough that a concurrent lane on the SAME host can push the branch + open the PR inside it — re-read for a NEWER competing PR right before you start writing, not only at claim time.** Measured on #1668 (base `4e98ede4`): my signed claim posted 23:09:18Z; while I held the window and built the worktree, another implementer session pushed `refs/heads/fix/gh-api-jq-contract-1668` = `99f3cc18`, opened PR #1670 READY and posted its PR comment at 23:10:03Z — 45 s after my claim. My pre-work check had read the thread as "one dispatch + one stale implementer claim", so it missed a competitor starting in parallel. The exit is exactly rule 3c/#1189: do NOT start a second implementation, do NOT touch their branch/PR; verify with `git ls-remote origin '*<issue>*'` + `gh pr view <n> --json state,isDraft,headRefOid,title,body` that the delivery really exists (title AND body carry `Closes #N`), post `blocked … handover tll-planner` naming both shas and the PR number, remove your never-written worktree, then hold for re-dispatch. Cheap discriminator: `git ls-remote origin '<the branch name you are about to cut>'` — non-empty means STOP. Two implementers on one issue produce two PRs for one branch suffix; the duplicate is churn the reviewer must untangle.
- **A mirror-sync dispatch can carry two acceptance criteria that are mutually exclusive — measure both before writing, and escalate rather than ship a red gate.** Measured on #1456 (base `9d5e38d5`): the issue asked (a) dedupe the duplicated planner bullets AND land the host-only residual so `make fleet-host-sync-check BASE=origin/master` reaches 0 divergences. The seam compares with `actual.read_bytes() != expected`, so "0 divergences" demands the mirror be BYTE-IDENTICAL to the host file. But the host files were BEHIND master: they lacked the `#1423`/`#1427` content that `tests/test_fleet_lifecycle.py::test_lane_skills_carry_the_push_and_verify_rule` pins (planner 0 of 3 needles, implementer 0 of 6). Proven both directions on committed trees with CI's exact shape (`BASE=HEAD PROFILES_HOME=agents`): mirrors := host bytes ⇒ seam OK but `test_fleet_lifecycle` RED (13 FAIL); master text + host-only notes ⇒ guard GREEN (0 FAIL) but mirrors != host bytes. No state satisfies both. The discriminator is the LINE-SUPERSET test: if every host line is present in the reconciled tree (`host lines not in new tree = 0`), the host is behind and must REFRESH FROM master — a host action outside a write lane's remit; the tree change is only the dedupe + host-only additions. Also re-count the divergent lanes yourself: the issue said 3, the live seam reds on **4** (`tll-planner`, `tll-implementer`, `tll-pr-rebase`, **`tll-reviewer`**) — never trust the issue's lane count. Escalate with the measurement table, do not push a PR whose body claims a green gate it cannot have.
- **A RESUMED or re-dispatched task can already be pre-empted by a NEWER overlapping dispatch naming the SAME mirror files — measure for a live competitor BEFORE you rebase or push.** Measured on #1456/PR #1465: the resume dispatch told me to rebase and land the dedupe + additive residual, but `tll-planner` had dispatched **#1468** to the same lane 5 min EARLIER for the same dedupe on the same two `agents/<lane>/skills/<lane>/SKILL.md` files, and that session held the newer signed claim plus a LIVE `hermes -p <lane> chat --query-file ...` process with both mirrors already `M` in its worktree (its tree already reached the x1 target). Check three things before touching a dispatched mirror: (1) `git log --oneline -S'<distinctive phrase>' origin/master -- <mirror>` to see whether master ALREADY carries your content; (2) `ps -Ao pid,etime,command | grep 'hermes -p'` for a live lane on a sibling issue, and read that sibling thread's newest claims; (3) `gh pr view <n> --json mergeable,headRefOid` for your own PR. A dispatch that names files another live lane is editing must NOT be force-pushed (#1458/#1416): post the measured partition (`blocked · handover tll-planner`) naming the overlapping dispatch id and the exact host-line residual the other scope EXCLUDES, and rest the branch. Note a stale base can also make the work a no-op: master may already hold all but a few host-only lines.
- **Amending an OPEN PR's body with a second `Closes #N` (a planner amendment) needs a SECOND OpenSpec change bound to that N AND a PR-body that carries the two keywords as separate `Closes #` lines, each binding exactly one reference.** Measured on #1612/PR #1600 (merged `0d4879a0`): the amendment added `Closes #1612` beside `Closes #1586`, and `openspec_archive_check.py --pr <n>` then asks the #1109 mirror question for BOTH closes — so create + `openspec-record-pr`-archive a small change whose proposal carries `Issue: #1612` / `PR: #1600` (one change cannot bind two issues: `openspec_index._refs` returns one value per header). Two gotchas when rebuilding the body from `gh pr view <n> --json body`: appending to the fetched body usually leaves the PREVIOUS body's own closing line mid-text, giving a DUPLICATE `Closes #1586` (harmless to the gate but sloppy) — drop it; and `make pr-message-check`/`pr_closure.check` accept any number of single-reference `Closes #` lines, while the SQUASH COMMIT lands with the PR TITLE's binding, so keep the title unchanged and re-verify with `pr_body.py --check-commit-file <title+\n\n+body> --branch refs/heads/master`.
- **Copying a host `SKILL.md` into the tree is lossy unless you diff at BULLET granularity, and a bullet block runs to the next LIST ITEM or heading — not just the next `- **`.** A naive `replace(old,new)` on a bullet substring duplicates whole trailing sections (measured: the tail insert re-created `## Worktree default`…`## Handover protocol` twice). Parse blocks as the span from one `- ` / `## ` mark to the next; when deleting a block, also swallow ONE preceding blank separator; and when removing a single bullet inside a section, cut by physical line count until the next line starting `- `, never by the parser's whole-region span (the `### Starting a lane` push-and-verify bullet shares its region with two plain `- ` bullets and a line-based cut took all four). Always assert after the edit that the top-level `## ` section list is UNCHANGED and no double blank lines remain.

- **A seam that PRINTS a filesystem path + a test that GLOBS it must agree on ONE spelling, and the disagreement is invisible on Linux CI.** Measured on #1552: `fleet_host_reconcile.py` built `--profiles-home` with `.resolve()`, so it printed `/private/var/folders/...` while `tests/test_fleet_host_reconcile.py` globbed the UNRESOLVED `/var/folders/...`; red on macOS (`/var` is a symlink to `/private/var`), green on Linux runners where the two coincide. Fix by printing the HANDED spelling (`Path(raw).expanduser().absolute()`, never `resolve()` — reads/writes follow symlinks transparently), and pin it with a fixture that hands the seam a SYMLINKED path: that reproduces the macOS shape on ANY host, so the guard is RED against the pre-fix seam in Linux CI too. Rule of thumb: any cross-host path comparison needs a symlink-shaped fixture, not a "works on my mac" note.

- **A guard that asks `git ls-files` on the REAL checkout must survive the container identity, and its negative assertions must not pass on an empty read.** Measured on #1493/PR #1592: CI `validate` went RED because the test container runs as root over the runner-owned checkout, so plain `git ls-files` failed with empty stdout; "root findings.md is NOT tracked" passed VACUOUSLY while "findings/history.md IS tracked" failed. Resolve with a read-only `git -c safe.directory=* ls-files` AND an explicit "index is readable" assertion before any negative path check. In a LINKED worktree the container also needs the main `.git` mounted (`GIT_COMMON_DIR`), or git says "not a git repository" even with the override — reproduce locally with the same mount before pushing.
- **A PR that RENAMES/REMOVES a file other lanes still append to (the tracked `findings.md` class) goes GitHub-DIRTY on every sibling merge until rebased.** `git merge-tree` may report clean (rename detection) while GitHub's mergeability says CONFLICTING; fetch, rebase, let git carry the sibling's new sections into the renamed file (verify the record survived), regenerate `OPENSPEC.md` with `scripts/openspec_index.py --write`, re-run `openspec-archive-check --pr <n>`, and push with an explicit lease. Also: a force-push can register ZERO check-runs on a head for no visible reason — confirm fresh run IDs exist (`gh run list --branch <b>`), and if none appear, the next rebase/push is what finally registers CI; never call a no-job head green.
- **A sibling rulebook pin that asserts `endswith(<its own clause>)` on a SHARED appended line contradicts any later landing's mandated order — measure both orders against BOTH modules before writing, then escalate; never silently pick one.** Measured on #1586/PR #1600: the dispatch mandated the §7b `Rule 3c note` read `#1209, #1232, #1258, #1395, #1589, #1586`, but #1482 (merged `edbf2fd0`) pins `tests/test_agents_store_rows.py::test_rule_3c_note_records_the_1395_provenance` with `note.endswith(CHANGE_2)`, CHANGE_2 being its `#1395` clause. Proven by execution on the real tree: order A (`…#1589, #1586`) → `test_dispatch_guard.py` rc=0, `test_agents_store_rows.py` rc=1 (`FAIL … ends with the approved CHANGE 2 clause`); order B (`…#1586, #1395`) → `test_agents_store_rows.py` 8/0, `test_dispatch_guard.py` rc=0. The two are mutually exclusive, so NO text satisfies both and #1482's merged pin is outside a sibling issue's remit. Write the mandated order, capture the both-orders execution table, post a signed `blocked … handover tll-planner` naming the exact assertion plus the alternative, and REST — do not edit the sibling pin or invert the order to chase green. The fix belongs to a planner-dispatched follow-up relaxing `endswith` to a presence + ascending-order assertion.
- **`git reset --hard <commit>` to discard surplus generated-index commits discards EVERY commit after it — re-add whatever you still need (e.g. `findings/<issue>.md`) BEFORE pushing.** Measured on #1586: I reset from three index-regeneration commits back to the openspec-record commit to collapse the conflict surface, silently dropping the `findings/1586.md` commit; `file_findings --check` then rediscovered `findings/1586.md is missing`. After ANY history-rewriting reset, re-run the whole fast gate list (`tests/test_<module>.py`, `make lint`, `architecture_check`, `lint_linefeeds`, `openspec-check`, `openspec-index-check`, `file_findings --check`) rather than trusting the pre-reset greens.
- **A generated-file regeneration left UNCOMMITTED is silently reverted by your own trial `git merge --no-commit` cleanup, and the next `openspec_index.py --check` then reads the STALE count from HEAD.** Measured on #1596/PR #1614: after `scripts/openspec_index.py --write` (`archived: **513**`) I ran the merge-tree simulation in a linked worktree and read `drifted by 1 ... says 'archived: **512**'` — because the merged tree took the COMMITTED `OPENSPEC.md` (512), not my uncommitted edit. Rule: stage/commit the regenerated artifact BEFORE any merge-tree probe, and confirm the probe's tree shows the regenerated value (`grep 'Active changes:'` inside the merged tree) rather than inferring it from the working tree.

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
  re-run bare to read the real exit code. **`pr_closure.py` is a VALIDATOR ONLY — it does NOT
  create the pull request** (`--help` says "Does this PR close the issue it implements?"). After it
  prints `OK: <branch> closes #<issue>`, open the PR explicitly with `gh pr create --repo <o>/<r>
  --base master --head <branch> --title "... (Closes #<issue>)" --body-file <f>` and confirm the
  returned URL with `gh pr view <n> --json state,headRefOid,baseRefName,mergeable`. Running the
  validator and assuming a PR now exists leaves `gh pr list --head <branch>` empty — check that
  list before reporting a PR to the planner.
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
- **A background check-poller that starts BEFORE a force-push reports the OLD run's verdict and is
  worthless — do not re-fix on it.** `gh pr checks` hides superseded runs, but a poller that
  snapshotted early captured the pre-push `fail` (e.g. a dead-test/lint red you already fixed). When a
  batch of background results shows `validate=fail`, first prove whether it predates the current head:
  fresh `gh pr view <n> --json headRefOid` + `gh pr checks <n>` (new run/job ids). If the poll started
  before the push, discard it, kill it if still alive, and start a NEW poll AFTER the push to the exact
  head. Reporting a stale fail to the planner restarts a verify cycle against a sha that never failed.
- **Re-running a scratch poll/helper script across sessions trips `write_file`'s stale-write guard**
  (`Refusing to overwrite <file>: exists but this task has not seen its full content`). Do not fight it:
  either inline the bounded loop directly in the `terminal` command, or write a fresh uniquely-named
  file. Only `patch` (after a fresh `read_file`) edits content you did not author this session.
- **Never concat a string and an object field in one `--jq` expression.** `'".state="+(.state)+"
  .merge="+(.mergeCommit)'` dies with `cannot add: string and object` because `mergeCommit` is an
  object, not a string. Access the sub-field (`+.mergeCommit.oid`) or use string interpolation
  (`"state=\(.state) merge=\(.mergeCommit.oid // \"-\")"`).

## Rule-3c §8-row landings (protected AGENTS.md, #1602 shape)

- **`make findings-check-for-pr FINDINGS_BRANCH=<b> BODY_FILE=<body>` belongs in the FAST offline list and must run BEFORE the first push** — it is not in the documented trio. Measured on #1602/PR #1608: I pushed head `517b9a86`, ran `closure`/`guard`, then discovered `findings/1602.md is missing` only after checking the gate by hand; the fix was a third commit `3d2d5181`. The composer's PR body + branch name resolve the per-issue file, so run it the moment the body file exists.
- **A `findings/<issue>.md` may carry MORE THAN ONE `## <title>` section, but every one needs `- **Evidence:**`, `- **Why:**` and `- **Done when:**`** (`scripts/file_findings.py::_REQUIRED`; `Signature`/`Owed-row` optional). Measured: a second section titled `What this landing touched` with prose bullets reds `finding '…' is missing Evidence, Why, Done when`. Keep the required field lines verbatim (`- **Field:** text`) even for a residual you are NOT fixing — the file is a record, not a work plan.
- **An OpenSpec change bound to `Issue: #N` is owed whenever the PR closes an issue that names no change** (#1109 prong of `openspec_archive_check.py`): create the dir, then open the PR, then `make openspec-record-pr ISSUE=<n> PR=<pr>` (writes `PR:` + archives + regenerates `OPENSPEC.md`), then `python3 scripts/openspec_archive_check.py --pr <pr>` must print `no active change left unarchived`. Do all of it BEFORE waiting on CI.
- **Commit message for an implementation-shaped PR = the five-section MESSAGE PATTERN, title carrying `Closes #<id>`** — never a terse `docs(rulebook): …` subject with bare prose. A squash lands on `refs/heads/master` which encodes no issue, so `implemented_issue_from_message` reads the `implements? #<n>` claim or the closing binding from the TITLE. Verify green via `python3 scripts/pr_body.py --check-commit-file <msg> --branch <b>`.
- **Test a names-only row pin RED/GREEN on scratch trees of the base**: copy the base into a scratch dir, apply the row + the pin, assert `PASSED 26 | FAILED 0`; delete the row and assert exit 1. The real ledger (`owed_rows_check.py`) gives the `LANDED AGENTS.md:<line>` evidence in the same run.
- **`git rebase --continue` ALSO strips `#`-prefixed lines from commit messages**, so a message that passed `--check-commit-file` before the rebase can ship with zero `## ` sections after it. Fix on the rebased head without re-resolving conflicts: rewrite the sequence todo with `GIT_SEQUENCE_EDITOR` inserting an `exec git commit --amend --cleanup=verbatim -F <msgfile>` line after each `pick`, then `GIT_EDITOR=true git rebase -i <upstream>`. Re-grep `^## ` = 5 on every commit before pushing.
- **A PR whose `validate`+`live-smoke` are green can still never merge while master churns**: qa-validate's `auto-merge-rebase` step runs BEFORE the squash and, when the branch is behind, pushes a rebased head and SKIPS the squash; that push lands `action_required` with ZERO jobs, so no run ever validates the new head. Measured on #1602/PR #1608 across four cycles (three green validate runs, three zero-job rebase heads). Recovery per cycle: fetch the branch, `git reset --hard origin/<branch>`, re-verify the rebased tree locally (index check, archive-check `--pr`, focused module, findings gate), then push an owner-host EMPTY commit (`chore(ci): retrigger CI on the auto-merge-rebased head (issue #1115 class)`, authored as the repo agent identity) so a real `pull_request` run fires. Expect several cycles when the fleet is busy; never call a zero-job head green.

- **Resolve an `OPENSPEC.md` rebase conflict with `python3 scripts/openspec_index.py --write` → `git add OPENSPEC.md` → `GIT_EDITOR=true git rebase --continue`, NEVER with `git commit`.** Measured on #1363/PR #1609: `git commit` during a conflict leaves HEAD detached with `rebase-merge` still active; the next push reports `Everything up-to-date` because the BRANCH pointer never moved, and the pushed head ships a stale index. After every `--continue`, check `git status -sb` names the branch (not `HEAD (no branch)`), `python3 scripts/openspec_index.py --check` is OK, and `git ls-remote origin refs/heads/<branch>` matches the sha you intend to push. Squashing several rebase-generated index commits into one on the current master tip cuts the conflict surface from 3–5 hops to 1.
- **A `#1115`-class recovery (never-started head / conflicting bot branch) is drivable from a HOST worktree through `scripts/pr_health.py::_push_to_pr_head`, not only via `make auto-merge-rebase`.** Measured on #1651/PR #1658: rebase the branch in a throwaway worktree off the fetched tip, regenerate the generated pair (`scripts/openspec_index.py --write`; `ARCHITECTURE.md`'s block only if it drifts), then import `pr_health` and call its OWN push body with `GIT_PUSH_PAT` set — `pat_push_url(origin_cfg, pat)` rewrites the github HTTPS origin, and `_git(wt, "push", f"--force-with-lease=refs/heads/{head}:{lease}", target, f"HEAD:refs/heads/{head}")` pins the lease to the remote sha fetched THAT run. Do NOT go through `make auto-merge-rebase`: `auto_merge_rebase.classify` refuses a CONFLICTING PR (`action="conflict"`), so the seam that resolves a conflicting branch is the lower-level `rebase_and_push`/`sync_branch` core — but a host recovery that already resolved the conflicts itself should just reuse `_push_to_pr_head` so the credential class is identical to the CI path. PROOF after the push is two reads, never the local intent string: `gh run view <id> --json jobs` must list real jobs AND `gh api repos/<o>/<r>/actions/runs/<id>` must show actor=`<owner login>` (type User) — a Bot actor means the checkout-credential path ran and the head will sit `action_required`/0-jobs no matter what `GIT_PUSH_PAT` was set to.

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
- **A RED-first test for a regex/reachability widening must FAIL as a `check()`, never CRASH on the
  pre-change module.** The old regex had ONE capture group, the new one has TWO (an optional outer
  group plus the target). Writing `m.group(2)` in the test throws `IndexError` on the old module and
  aborts the whole module mid-test, hiding the later genuine FAILs. Read groups defensively
  (`g = m.groups(); g[-1] if g else None`) and avoid referencing attributes that only exist after
  the fix (e.g. a new `HOP_AT_PREFIX`) in the real-tree section — use `raw.lstrip("@")` inline so
  the old module still runs and accumulates all its FAILs. Verify RED by exit code (base rc=1,
  head rc=0), not by a grep count that a crash can truncate.
- **To prove an issue's "planted defect" end-to-end across old vs new guard, run BOTH real CLIs over
  the SAME temp Makefile built from the real tree.** The pre-change script's internal
  `import architecture_bot` fails from a bare temp path: run it with `cwd=<repo>` and
  `PYTHONPATH=<repo>/scripts` (subprocess env) so its imports resolve, while passing
  `--makefile <temp>` so the checkout stays untouched. A clean OLD rc=0 vs NEW rc=1 on that exact
  planted shape is stronger evidence than synthetic fixtures alone, and it is the fastest way to
  measure whether the reported hole is actually reachable on the current tree.

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
- **A write-time refusal seam must build its carriers map from the ALREADY-MERGED store only,** so only a copy ARRIVING at ingest is refused — an established owner re-capturing its own tuple is always kept (`others = carriers - {self}` empty), and a copy+owner in one snapshot never double-refuses. Never build carriers from batch+store. Refuse by ownership (name the owning model id in the log), keep one `CROSS_MODEL_ALLOW_LIST` as the single source of truth imported by both the validator and the test, and ship a no-mock E2E that runs the real `ingest_raw_snapshots` in a `TRENDING_DATA_DIR` temp dir (`since=None` merges any raw) asserting the copy did NOT merge while a legit measurement on the same raw row DID. Recipe in `references/data-fix-hygiene.md` §7.
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
- **A dispatch whose acceptance is an `AGENTS.md` edit CANNOT land in a headless lane — detect it before building the change and hand over fast.** The harness `_check_protected_instruction_write` prompts for one-operation approval on EVERY write to protected instruction files (`AGENTS.md`, `SOUL.md`, …) and fails closed when no human channel answers: `BLOCKED: write to protected agent-instruction file(s) (AGENTS.md) approval prompt timed out without a user response. Silence is not consent. Do NOT retry it or attempt the same edit via another path (terminal, execute_code, etc.).` Measured on #1402 (base `d4096735`): the entire issue was a §4 first-bullet correction, so NO PR was possible — retrying, or routing the edit through `terminal`/`execute_code`, is forbidden (rule 3c: the sign-off is a human act). What lands instead: keep the prepared worktree + OpenSpec change, write the §4 task box AT CREATION as `- [~] … blocked: rule 3c human sign-off (AGENTS.md protected in a headless leg)`, and post a signed `blocked … handover owner` comment carrying the exact diff so an attended run (owner approving the prompt) finishes in one step. Grep the dispatch's DONE wording for `AGENTS.md` up front.
- **A `$(PYTHON_RUN)`-routed gate that reads `$GITHUB_EVENT_PATH` dies `FileNotFoundError`.** `$GITHUB_EVENT_PATH` is a RUNNER path, so the container does not mount it; measured on #1454/PR #1480. Keep any target that reads the webhook payload HOST-side (like `make pr-closure`) — never route it through `PYTHON_RUN`.
- **A CONCURRENT writer can commit from the SAME worktree you are editing — `git status` can show your own in-progress edit already inside someone else's commit.** Measured on #1454/PR #1480: an unattributed attended run on the same host pushed `ceb48d11` while my edits sat uncommitted; its `git add -A && git commit` swept my half-applied patch in and shipped a DUPLICATE `GATES` key in `findings.md`. Before committing, re-read `git log --oneline -3` AND `git status`; if an unattributed commit appeared, reset to the remote head, re-apply only what is still missing, and push with an explicit `--force-with-lease=<branch>:<sha-you-last-saw>` so a newer sibling push REJECTS instead of being clobbered. Report the collision on the issue thread naming both shas — do not `git add -A` blindly in a tree another actor may share.
- **A planner amendment that adds a SECOND `Closes #N` to the PR body needs a SECOND OpenSpec change bound to that issue — one change cannot bind two.** `openspec_index._refs` returns one value per `Issue:` header (a second `Issue:` line overwrites the first), so `make openspec-archive-check PR=<n>` reds `CLOSE of #N — NO OpenSpec change (active or archived) names Issue: #N` after a sibling adds e.g. `Closes #1593` alongside `Closes #1496`. Keep both closing keywords (the planner ordered them), create a small ARCHIVED change with its own `Issue: #N` / `PR: <n>` header, proposal, capability spec with Given/When/Then + resolving `- **Test:**` lines, ticked tasks, and a requirement title DISTINCT from the existing change's (or `openspec-duplicate-check` objects), then `make openspec-index` and re-run archive-check until it names both issues.
- **An implementation-shaped PR now needs `findings/<issue>.md`, not root `findings.md` (issue #1493).** CI's `findings-check-for-pr` reds `findings/1496.md is missing` after ~12 min even when local `make findings-check` (which checks the ROOT file) is green. Author the per-issue file with `## <title>` + `**Signature:**` / `**Evidence:**` / `**Why:**` / `**Done when:**`, and verify with `make findings-check-for-pr FINDINGS_BRANCH=<branch> BODY_FILE=<pr-body>` — never write `- none` if you actually found defects during the repair.
- **A branch cut BEFORE #1493 carries its analysis at the old shared seam (`findings/history.md`), so it stays green until a rebase onto a post-#1493 master exposes the gap.** Fix by ADDING `findings/<issue>.md` — the gate resolves it from the BRANCH-encoded issue, so the `-<id>` suffix is what binds it — and leave every existing `history.md` section byte-untouched; never re-home or delete the old section. Measured on #1559/PR #1561: head `a9325faa` red `[findings] FAIL …/findings/1559.md is missing`; one 8-line section turned step 9 green. It surfaces together with the merge-tree index red after the same rebase, so fix both in one push. Measured again on #1596/PR #1614 (dispatch 14:53:32Z): head `77fd97e7`, two findings sections, same 26s rule-6g red.
- **Resolving a rebase conflict by taking master's side of `ARCHITECTURE.md` silently drops your hand-written §6 target/script rows.** `make architecture-check` then reds `make target … is not described` / `script … has no row in §6` while `make architecture-refresh` only fixes the generated inventory block. Restore the two rows verbatim from the pre-rebase commit (`git show <old-head>:ARCHITECTURE.md | grep '<name>'`) and re-run `architecture-check` BEFORE pushing.
- **When a sibling session force-pushes your PR branch mid-repair, the lease rejection is a feature — preserve their commits, do not overwrite.** Read `git ls-remote origin refs/heads/<branch>`, fetch it, save your local head as a backup branch, reset to the sibling tip, rebase/cherry-pick your unique commits on top, regenerate both generated files, and push with `--force-with-lease=<branch>:<actual-tip>`. Repeat until master stops moving; the merge-tree gate only goes green on a head that already contains the tip CI will merge. Verify final delivery with `gh pr view <n> --json state,mergedAt,mergeCommit` AND `gh issue view <id> --json state,closedAt` — then post `BOT … done #<id> · handover tll-planner`.
