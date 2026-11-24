# Findings

## The AGENTS.md rows for the shape-aware analysis gate are owed to a protected rulebook

- **Signature:** owed-row-findings-shape-gate
- **Evidence:** this change adds a step to `.github/workflows/qa-validate.yml`'s `validate` job and the target `make findings-check-for-pr`; the architect's design for #1454 declares three AGENTS.md edits (a §6g sentence naming the gate, the §6b `qa-validate.yml` bullet naming the step, and a §8 guard row), and a headless leg is REFUSED the write to that protected agent-instruction file (rule 3c)
- **Why:** an undeclared owed row vanishes — either the PR goes red on an unticked box, or the rulebook keeps describing the pre-gate behaviour while the pipeline enforces something else, so the rule 6g duty stops being readable from the rulebook
- **Done when:** an attended run lands the §6g sentence, the §6b bullet and the §8 guard row from this ledger issue
- **Owed-row:** <!-- owed-row: section=8 needle="make findings-check-for-pr" -->

## Landing host-ahead notes verbatim would reintroduce the duplicate-bullet defect

- **Evidence:** `make fleet-host-sync-check BASE=origin/master` RED on 4 lane skills at `198901c7`; difflib of host vs base blobs gives planner +11/0, reviewer +2/0, implementer +3/0, pr-rebase +1/0. The planner/reviewer additions are interleaved or verbatim duplicates of bullets already on master; the orphan clause `BEFORE waiting on CI; doing this only after seeing the red` already exists once at `agents/tll-implementer/skills/tll-implementer/SKILL.md:218`.
- **Why:** the sync gate compares bytes and cannot distinguish a legitimate forward note from a duplicated fragment, so copying host bytes to master would undo issues #1455/#1456/#1462/#1469; only three implementer notes are genuinely new.
- **Done when:** a reviewed PR lands only those three notes with a count guard, no host file is overwritten, and the remaining host-only duplicate fragments are curated in separate changes.

## The AGENTS.md rows for the role-based bot-health alarm are owed to a protected rulebook

- **Evidence:** this change makes `scripts/bot_health.py` derive pipelines by role (cron + dispatch-only) and read each by its own event, and joins `bot-health.yml` to `MAIN_PIPELINES` / `DISPATCH_ONLY_PIPELINES`; AGENTS.md §6b's `bot-health.yml` bullet (currently "derives the cron pipelines … newest N scheduled runs") and §8's guard row describe the pre-change seam, and a headless leg is REFUSED the write to that protected agent-instruction file (rule 3c).
- **Why:** an undeclared owed row vanishes — either the PR goes red on an unticked box, or the rulebook keeps describing a cron-only alarm while the code reads dispatch-only runs, so the reader cannot tell that this alarm now watches itself.
- **Done when:** an attended run lands the §6b bullet (role-based selection, `schedule` for cron / `workflow_dispatch` for dispatch-only) and a §8 row naming `tests/test_bot_health.py` guards, citing #1186 and this PR, from this ledger issue.
- **Owed-row:** <!-- owed-row: section=8 needle="test_dispatch_only_pipelines_are_watched_by_role" -->

## Every archived OpenSpec capability spec keeps a `TBD` Purpose that nothing fills

- **Evidence:** `openspec/specs/<capability>/spec.md` is written by `openspec archive`, and its
  `## Purpose` is the literal placeholder `TBD - created by archiving change <name>. Update
  Purpose after archive.` Measured on this tree: all 37 aggregated specs carry it, e.g.
  `openspec/specs/agent-leg-skills/spec.md` (`## Purpose` → `TBD - created by archiving change
  agent-leg-skills. Update Purpose after archive.`), and the new
  `openspec/specs/fleet-mirror-union/spec.md` written by `make openspec-archive
  NAME=fleet-mirror-union-zero-to-n-1478` carries the same placeholder. No gate reads the
  `Purpose` text, so the reminder is never actioned.
- **Why:** the aggregated spec set is the readable form of the rulebook's capabilities; a
  permanent `TBD` Purpose on every capability hides which behaviour each one owns, and the
  "Update Purpose after archive" instruction has no owner, so it rots silently on every future
  archive.
- **Done when:** the archive seam (or a follow-up gate) either derives a real one-line Purpose
  from the archived proposal's `## Why` / `## What Changes`, or the placeholder is replaced by a
  stated default and the "update after archive" instruction is dropped from the template.

## The tracked `findings.md` makes every implementation PR conflict with every sibling

- **Evidence:** `findings.md` is tracked on master and each implementation PR APPENDS its own `## <title>` section (rule 3b additive). Measured on this lane's PR #1488 inside one run: master `198901c7` -> `9c15447` (#1487 appended a section) and then -> `6924f02` (#1186 appended a section); after EACH move `git merge-tree origin/master HEAD` answered `CONFLICT (content): Merge conflict in findings.md`, and `auto-merge` refused twice with `Pull request #1488 is not mergeable: the merge commit cannot be cleanly created`.
- **Why:** one shared append point means EVERY landing implementation PR invalidates the merge commit of EVERY other open one — the quiet queue-wide red class (#1359), now mechanical and reproducible instead of occasional.
- **Done when:** each implementation's analysis lands where it cannot collide (a per-PR path, or an issue-linked artifact the gate reads), or the gate unions the file mechanically instead of demanding a rebase per sibling.

## The AGENTS.md §6r sentence and §8 guard row for the filer's error-block order are owed to a protected rulebook

- **Signature:** owed-row-filer-error-block-order
- **Evidence:** `scripts/pipeline_failure_issue.py::extract_error_block` now presents the failing region's own lines first and marks everything from another step region as `[filer] … FILLER …`, while `AGENTS.md:926` still says that chatter is "always presented in log order" and the §8 guard row at `AGENTS.md:2425` still says "the block keeps log order"; a headless leg is REFUSED the write to that protected agent-instruction file (rule 3c), and the replacement wording is declared on issue #1466
- **Why:** the rulebook would keep describing the pre-#1466 ordering the code no longer has, so a later reader re-derives the defect the issue exists to remove; the rule 3c sign-off is a human act
- **Done when:** an attended run lands the §6r presentation sentence and the §8 guard row declared on issue #1466
- **Owed-row:** <!-- owed-row: section=8 needle="make pipeline-failure-issue" -->

## The host RED-first note was forward work and must be landed, not wiped

- **Evidence:** `make fleet-host-sync-check BASE=origin/master` RED against `ea823544` on `tll-implementer/skills/tll-implementer/SKILL.md`; `diff -u` of base blob vs live host file gives 3 added content lines and 0 deletions (`7. RED-first: ...` plus a duplicate `## This lane`). The live file mtime 2026-11-24 04:34:40Z falls inside the active `tll-planner` lane run `8e5417464966` (started 03:26:17Z).
- **Why:** the sync gate compares bytes and cannot distinguish a legitimate forward note from staleness; copying the base over it would delete work an active lane just wrote and repeat the false-alarm this step exists to prevent. The duplicate heading is noise and is excluded from the landing.
- **Done when:** a reviewed PR lands only the genuinely-new clause in the tracked skill, the host file stays intact with a timestamped backup, and the fleet-sync gate goes green after the merge and base re-sync.

## The planner DEAD-lane RESUME note is forward work and must be landed, not wiped

- **Evidence:** after PR #1499 merged (master `16481506`), `make fleet-host-sync-check BASE=origin/master` stayed RED on `tll-planner/skills/tll-planner/SKILL.md`; `diff -u` of the base blob against the live host file gives 9 added lines and 0 deletions, the new `A pushed branch with NO PR is a DEAD lane` clause with measured #1467 evidence. The host file was backed up before any copy.
- **Why:** a byte-exact gate cannot distinguish a genuine forward note from staleness, and overwriting it would delete work an active planner lane wrote; only the additive landing makes the gate green without loss.
- **Done when:** a reviewed PR lands the clause in the tracked planner skill, the host file stays intact with a timestamped backup, and the fleet-sync gate goes green after the merge and base re-sync.



## The AGENTS.md §6r behaviour bullet and the §8 guard row for the filer window are owed to a protected rulebook

- **Evidence:** this change makes the failure filer's candidate set the UNION of a paginating `window_runs()` walk of the REST `actions/runs` pages (replacing BOTH fixed `--limit 30` literals, `main_pipeline_failures` and `pr_triggered_failures`) and `reconcile_marker_runs()`, which fetches every unfiled marker-carrying run directly by id; the marker-matched backfill now records the marker issue's number/url instead of null, and `pipeline_failure_guard_check.marker_issue_states` delegates to the ONE `failure_issue_markers` seam. Measured RED-first: the five AC tests in `tests/test_pipeline_failure_issue.py` produce 13 failed checks against `git show origin/master:scripts/pipeline_failure_issue.py` and 0 against this head (281 checks green). A headless leg is REFUSED the write to `AGENTS.md` (rule 3c).
- **Why:** an undeclared owed row vanishes — either the PR goes red on an unticked box, or the rulebook keeps describing a capped 30-run scan while the code pages the whole window, so the next reader cannot tell that a filed failure is reconciled regardless of its rank. The sign-off is deliberately a person's act.
- **Done when:** an attended run lands the §6r clause and the §8 guard row below, and ticks the blocked tasks.md box.
- **Owed-row:** <!-- owed-row: section=6r needle="make pipeline-failure-issue" -->
- **Owed-row:** <!-- owed-row: section=8 needle="tests/test_pipeline_failure_issue.py" -->
- **Full §6r text (insert after `run in its window (`--window-hours`, default 192 — a full weekly cadence plus grace, since the` / `filer rides the sweep) it fetches each failing job's log`):** ` — **the candidate set is the UNION of a paginating window walk and a marker reconcile (issue #1467):** both scans page the REST `actions/runs` feed until a page's OLDEST run leaves the window (a page-capped walk prints a loud partial-window line instead of reading a capped view as complete), `reconcile_marker_runs()` fetches every unfiled marker-carrying run DIRECTLY by id so a filed failure joins the ledger regardless of its rank in any run list, the marker-matched backfill records the marker issue's number/url, and the PR-blockage half shares both seams**`
- **Full §8 text (append to the existing `tests/test_pipeline_failure_issue.py + make pipeline-failure-issue` row):** `**and (issue #1467) the candidate set covers the whole window: BOTH scans (`main_pipeline_failures` and `pr_triggered_failures`) go through ONE paginating `window_runs()` walk of the REST `actions/runs` pages rather than a fixed `--limit 30`, a page-capped walk is loud, every unfiled marker-carrying run is fetched DIRECTLY by id through `reconcile_marker_runs()` so a filed failure joins the ledger regardless of its list rank, the marker-matched backfill records the marker issue's number/url instead of null, `pipeline_failure_guard_check.marker_issue_states` delegates to the SAME `failure_issue_markers` seam, and the RED-first AC1–AC5 tests fail on `origin/master`'s script**`

## fix_loop.sh misclassifies a restored self-archive dismantle as "guard could not run"

- **Evidence:** `scripts/fix_loop.sh:318-323` captures `sa_rc=$?` from `make self-archive-guard` and branches on `if [ "$sa_rc" = "1" ]` for the "dismantled its own OpenSpec change — the guard restored it" note, falling through to `elif [ "$sa_rc" != "0" ]` → "[fix-loop] self-archive guard could not run (exit $sa_rc)". Measured on this worktree with a real dismantle: the container-routed guard printed `self-archive: … was dismantled mid-run — the guard restored it` and its script exited 1, but `make` wrapped the recipe failure as `MAKE_RC=2` (verified without a pipe), so fix_loop takes the "could not run" branch and never emits the restoration note. Reproduce: move a baseline-active change into `openspec/changes/archive/`, then `SELF_ARCHIVE_BASELINE=<baseline> SELF_ARCHIVE_REF=<sha> SELF_ARCHIVE_RESTORE=1 make self-archive-guard; echo $?`.
- **Why:** `make` returns 2 whenever a recipe exits non-zero; the script's 1 is not the make exit code. The #812 protection still works (the change is restored and the loop stays red), but the operator-facing diagnosis is wrong — the loop reports "could not run" for a guard that ran and restored a real dismantle, so a reader of the fix notes cannot tell a restored self-archive from an unreadable baseline.
- **Done when:** `fix_loop.sh` maps the make exit code to the guard's outcome without losing the distinction (e.g. branch on the guard's own verdict line, or accept both 1 and 2 as a red guard with a distinct note for an actual read failure), a regression test drives the real `make self-archive-guard` with a planted dismantle and asserts the "restored" note appears (and that a missing baseline still reports "could not run"), and the change lands in its own reviewed PR with a `tech-debt` issue — rule 6g forbids fixing it in the change that found it.

## The filer files ONE ISSUE PER RUN, so a recurring state-gate red becomes dozens of near-identical issues

- **Evidence:** the host filer sweep at 2026-11-24T05:34–05:38Z created issues #1506–#1552 (47 issues in ~4 min). Reading each body's own `Failing step(s) per GitHub's own job steps:` line: **38 of 47 name the same step**, `OpenSpec gate (changes validate, tasks ticked, index current)`; the rest are 2× `OpenSpec lifecycle…`, 2× `OpenSpec index on the merge tree (issue`, and four other singletons. Open issues #1437 / #1450 / #1459 / #1471 / #1484 already track individual runs of that same OpenSpec-gate step. `make pipeline-failure-issue` keys its master/schedule half on the run id alone (`scripts/pipeline_failure_issue.py::main_pipeline_failures`), so every new red run of one defect files again.
- **Why:** this is the exact defect #1476 removes for the PR-blockage half and it is still present in the master/schedule half — a fleet-wide recurring red produces a 40+ issue backlog that buries the signal, and each new sweep re-files it because nothing groups by error class. The #1476 change deliberately does not touch this half (outside its scope), so it is filed here rather than folded into the change that revealed it (rule 6g).
- **Done when:** the master/schedule half groups concluded-bad runs by a STABLE error-class key (the failing step + the first strong error line, the same anchor #1476 adds for the PR half) and files ONE issue per class per window, with the per-run ledger rows still appended (append-only, rule 3b); a regression test plants N runs of one class across a window and asserts one issue + N rows.

## Two hosts claimed #1495 eight seconds apart inside one watcher cycle

- **Evidence:** on issue #1495 my claim `7123599719` landed 2026-11-24T06:06:57Z and `asimov@mac`'s `7123602032` landed 06:07:05Z — 8 s later, both after the same ~06:01Z wake-up. `AGENTS.md` §7b pins the settle window at 180 s from a wake-up (`scripts/watch_monitor.py::CLAIM_SETTLE_SECONDS`), but each host measures it from its OWN wake, so two hosts woken by the same monitor tick can both satisfy the floor and still collide. This is the #1312 shape recurring.
- **Why:** the floor was added to stop exactly this duplicate claim; measured again it does not separate two hosts that share a wake-up. A cross-host claim needs a board-visible ordering a local timer cannot provide.
- **Done when:** the fleet protocol gives a claim a cross-host ordering the loser can read before starting (for example the planner's dispatch comment id as the claim's parent, or a single shared claim record), with a guard that reproduces the 8 s double claim and fails when the ordering is dropped.

## Two more test modules build their ingest replay tree inside the checkout

- **Evidence:** `tests/test_cross_model_attribution.py:493` sets `tmp = ROOT / "tmp-ig702-e2e"` and removes it with `shutil_rmtree(tmp, ignore_errors=True)` (lines 495 and 511); `tests/test_weight_gb_contradiction.py:248` sets `tmp = ROOT / "tmp-ig615-e2e"` and removes it with `shutil.rmtree(tmp, ignore_errors=True)`. Both are the exact #1505 shape this change fixes in `tests/test_ingest_refusal_grouping.py` — an untracked, non-gitignored scratch directory inside the repository working tree whose failed cleanup is silently swallowed. Measured by grep over `tests/*.py` at the branch head `cbe43d17`.
- **Why:** the same hazard recurs: a surviving `tmp-ig702-e2e/` or `tmp-ig615-e2e/` is one `git add -A` away from being committed by any lane, and a container-identity leftover makes the removal fail quietly — which is how the #1494 sweep staged thousands of scratch files. Fixing only the module that filed the issue leaves the class alive in two siblings.
- **Done when:** both modules build their replay tree under a temp dir outside the checkout and remove it loudly (the same `_scratch`/`_remove` discipline, or a shared helper), each pinned by a guard that is RED on the in-checkout path.

## A bound draft PR is invisible to the board and to auto-merge

- **Evidence:** `scripts/pr_health.py::findings` has always skipped `isDraft` PRs ("a draft is allowed to be quiet"); `qa-validate.yml`'s `auto-merge` job gates on `github.event.pull_request.draft == false`, and `scripts/auto_merge_rebase.py::classify` answers `draft` → "untouched". The ready/never-draft rule existed only as prose in the lane skills, so a finished change parked as a draft stalled green with no signal naming it.
- **Why:** the one classifier that sees every open PR could not name a bound draft, so the board hid work that was actually done and no gate failed. A CI-side `github.event.pull_request.draft` assertion would need a `pull_request` trigger on the dispatch-only `pr-health.yml`, re-running the rebaser on every PR update.
- **Done when:** `pr_health.py` names a bound draft with its issue (`draft_findings`), `make pr-draft-check` reds on it, and both lane skills state "open every PR READY (never draft)" — this change; `qa-validate`'s existing merge-time draft guard is retained.
