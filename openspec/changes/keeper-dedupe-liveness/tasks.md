# Tasks: keeper-dedupe-liveness

- [x] Classify each open keeper live / tombstone / unmergeable in `scripts/keeper_pr.py`
- [x] Add the RED-first guards in `tests/test_keeper_pr.py` (green, checkless, red, in-flight)
- [x] Prove the guard RED against the base revision of the seam
- [x] Run `make lint`, the module, and `make test`
- [x] Write `findings.md`, regenerate `OPENSPEC.md` and run `make openspec-check`
- [x] Compose the PR body, open the PR, record and archive the change, push and monitor the checks

Evidence:

- RED on the base revision of the seam (`git show origin/master:scripts/keeper_pr.py`): **6 FAIL** —
  the checkless-mergeable, red-keeper and unmergeable flows all break, because the old
  predicate is a bare two-tuple that suppresses ANY mergeable keeper.
- GREEN after: a keeper with `validate`+`live-smoke` `success` suppresses; a MERGEABLE keeper
  with NO check objects is named `TOMBSTONE` and a fresh keeper lands; a `failure` check is a
  tombstone; an in-flight (`conclusion: null`) keeper still suppresses, so a live repairer is
  never duplicated.
- The liveness verdict is pure (`keeper_health`) and reads `statusCheckRollup`, a field the
  `gh pr list` contract already records (`scripts/gh_json_fields.py`), so no new gh command
  enters the tree.
- Measured on `master` `3d84c98`: `OPENSPEC.md` says `1 active / 413 archived` and disk holds
  1 + 413 — the count-line drift this issue also named is already repaired, so the code delta
  is the remaining work.
