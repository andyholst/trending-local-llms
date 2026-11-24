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
