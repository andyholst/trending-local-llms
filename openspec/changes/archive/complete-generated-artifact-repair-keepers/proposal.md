# Proposal: complete-generated-artifact-repair-keepers

## Why

A merged PR archives an OpenSpec change and moves a make target / script / workflow job, so BOTH generated artifacts (`OPENSPEC.md` index and `ARCHITECTURE.md` §10 inventory block) drift from the SAME event. The two event-driven repair keepers each regenerate only ONE artifact and land a single-file keeper, which then fails the sibling generated gate; neither auto-merges, master stays red on both gates, and every open PR's `validate`/`live-smoke` waits behind it (rule 6q). Measured 2026-11-22: master `48184330` red on both; PR #1331 failed at `openspec-index-check` (`Makefile:395`), PR #1332 at `architecture-check` (`Makefile:467`); index keepers #1323/#1326 both merged yet master stayed red. Owner-held PR #1302 is the same class.

## What Changes

- `index-repair` job: after its own classifier, also regenerate `ARCHITECTURE.md`'s block, and land a keeper naming BOTH files.
- `architecture-repair` job: after its own classifier, also regenerate `OPENSPEC.md`, and land a keeper naming BOTH files.
- `scripts/keeper_pr.py` already accepts a space-separated `FILE` list; no change there.

## Impact

Each post-merge repair job now produces a keeper green on BOTH generated gates, so one keeper can auto-merge and unblock master. The healthy "nothing to land" path in `keeper_pr.py` makes the second job a no-op once the first keeper lands.

## Not covered

- Does not rebase, regenerate the diff of, or close any existing keeper PR (#1302/#1331/#1332) — those remain owner/sweep decisions.
- Does not change the manual `make openspec-index` / `make architecture-refresh` targets or the generated-file format.
- Does not decide which DIRTY open PRs to close — that is an owner ruling.

Issue: #1339
PR: #1340
