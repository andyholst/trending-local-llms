# Proposal: architecture-rows-push-proves-ci

Issue: #1648
PR: #1652

## Why

PR #1631 landed the push-proves-CI contract (`rebased=true` is reported only after the PUSHED
sha's OWN `qa-validate.yml` run is read back with >0 jobs) and documented it in four hand-written
`ARCHITECTURE.md` rows. The rebase before its merge resolved an `ARCHITECTURE.md` conflict by
taking master's side and silently dropped all four clauses: measured, head `5eea2616` carried
them while the merged head `460f7100` had `grep -c 1616 ARCHITECTURE.md` = 0 and a file
byte-identical to master's — yet the PR body still claimed the rows. A reader of
`ARCHITECTURE.md` sees the pre-#1616 contract, which is exactly what this PR changed.

## What Changes

- Restore the four `ARCHITECTURE.md` rows verbatim from the pre-rebase head `5eea2616`: the
  `auto-merge-rebase` target row, the qa-validate `auto-merge` job row, and the
  `scripts/pr_health.py` / `scripts/auto_merge_rebase.py` script rows.
- Regenerate §10's inventory block through the tree's own generator
  (`make architecture-refresh`), never by hand, so the document stays green on
  `make architecture-check`.
- Add a RED-first row guard, `tests/test_architecture_rows_1616.py`, that reads the REAL
  `ARCHITECTURE.md` and asserts each clause sits in its own row; it exits 1 on master's
  `ARCHITECTURE.md` and 0 on the repaired head.
- Land on a NEW branch/PR (`Closes #1648`): #1631 merged at 2026-11-24T19:33:56Z mid-repair and
  its head branch was deleted, so the merged PR cannot be re-pushed.

## Impact

Docs and a guard only: no code, data format, contract, image, target, workflow-trigger or
schedule change, and no rulebook edit — the surviving `AGENTS.md` §8 pin is re-checked, not
rewritten. PR #1631's code (the `verify_rebased_ci` proof) is untouched; this repairs only the
documentation delta its rebase lost.

## Not covered

- No change to `scripts/pr_health.py` / `scripts/auto_merge_rebase.py` behaviour (that is
  #1616, already merged).
- No new make target, pipeline job, cron or collaborator grant.
- No edit to `AGENTS.md`: its §8 regression row already names the #1616 pin and is verified
  present, not modified.
