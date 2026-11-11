# Proposal: remove-stray-qa-notes

Issue: #390 — `tech-debt: the fix loop leaves qa-report.txt.notes in the repo tree and git add -A commits it`

## Why

#390 fixed the CAUSE — `scripts/fix_loop.sh` no longer creates `qa-report.txt.notes`
beside the report, and `.gitignore` now covers the `qa-report.txt.*` class (PR #392).

It could not fix the EFFECT: a file that is already tracked stays tracked, and
`.gitignore` never applies to it. PR #387 (the #376 implementation) merged at
2026-10-19T05:44:41Z — **before** #392 — carrying that 0-byte file at the repository
root (blob `e69de29`). `git ls-tree origin/master` lists `qa-report.txt.notes`
today, so master ships an empty scratch artifact: noise in every checkout, in every
`git status` a contributor reads, and a file the next `git add -A` keeps alive.

## What Changes

- **`qa-report.txt.notes` is removed from the tracked tree** (`git rm --cached`, the
  working copy deleted). The ignore rule from #392 already covers the class, so the
  removal is final rather than a one-commit gap.
- **`tests/test_fix_loop.py::test_no_scratch_report_file_is_tracked`** asserts that
  `git ls-files` finds nothing in the loop's scratch class (`qa-report.txt`,
  `qa-report.txt.*`, `comment.md`). Verified RED with the file restored
  (`[['qa-report.txt.notes']]`), GREEN after the removal.
- The tracked OpenSpec change listed in `OPENSPEC.md`.

## Impact

`qa-report.txt.notes` (deleted), `tests/test_fix_loop.py`, this OpenSpec change and
the regenerated `OPENSPEC.md`. No make target, stage, pipeline job, image or script
changes, so `ARCHITECTURE.md` is unchanged (rule 6h).

## Not covered

- **Every future scratch artifact a bot writes.** The class is gated for the fix
  loop's report siblings only; a bot that writes a new scratch file under a new name
  is still uncovered until it is ignored or moved out of the checkout.
- **`AGENTS.md` §8.** The row owed for #390's guard is #391 (the file is protected
  for agents); this change's guard reuses that row's subject and needs no new one.
