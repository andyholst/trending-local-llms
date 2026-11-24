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
