# Proposal: the weekly architecture keeper lands through the keeper-pr seam (issue #1081)

Issue: #1081 — "architecture-bot's keeper PR step is a fourth spelling of the
PR: #1113
keeper-landing shell #869 folded into scripts/keeper_pr.py"

## Why

Rule 6d: a coordinated act with one grammar has exactly ONE implementation.
Issue #869 folded the keeper-PR landing sequence (branch, agent identity, one
commit, push, composed body, `gh pr create`, mergeable-only dedupe) into
`scripts/keeper_pr.py` for three jobs — qa-validate's `index-repair` and
`architecture-repair`, and queued-alarm's ledger step. The weekly
`architecture-bot.yml` refresh job remained a **fourth spelling** of that shell
(`git switch -c`, `git push origin "HEAD:refs/heads/…"`, `make architecture-pr-body | gh pr create`),
out of #869's declared scope but the natural next change (issue #1081).

## What Changes

- `scripts/keeper_pr.py` lands a SPACE-SEPARATED SET of generated files (additive:
  a single file behaves exactly as before). It commits every owned file that
  changed and refuses when any change falls OUTSIDE its file set.
- `architecture-bot.yml`'s land step becomes ONE `make keeper-pr FILE="ARCHITECTURE.md
  OPENSPEC.md" BRANCH_PREFIX=ci/architecture-refresh DEDUPE=1 … BODY_TARGET=architecture-pr-body`
  invocation; the hand-written branch/commit/push/body shell is deleted.
- The weekly keeper's branch becomes `ci/architecture-refresh-<UTC>Z` (still Z-stamped
  so `pr_closure` reads no issue out of it), and it gains the #960 mergeable-only
  dedupe the seam carries — the old step had none, so a second run behind an open
  keeper filed a duplicate branch.
- `tests/test_keeper_pr.py` gains a multi-file landing test and its Done-when scan
  covers `architecture-bot.yml`; `tests/test_architecture_bot.py`'s shipped-run test
  executes the new step through the real seam script (stub `gh` answers `pr list`),
  pins the new branch shape, and pins that both generated files ride the seam.

## Impact

- Pipelines: `architecture-bot.yml` refresh job (landing step only; guard, drift
  gate and regeneration steps unchanged).
- Scripts: `scripts/keeper_pr.py` (multi-file `--file`), no Makefile seam change
  (`--file "$(FILE)"` carries the space-separated set unchanged).
- Tests: `tests/test_keeper_pr.py`, `tests/test_architecture_bot.py`.
- `ARCHITECTURE.md` §10 regenerates through `make architecture-refresh` in this change.

## Not covered

- `invalid-change-repair`'s multi-path archive-move keeper (#962) keeps its own
  shell — it moves directories, not files, and stays pinned by `tests/test_workflows.py`.
- No rule 3c change: `AGENTS.md` names no behaviour this change alters.
