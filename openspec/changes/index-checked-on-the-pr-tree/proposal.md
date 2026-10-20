# Proposal: index-checked-on-the-pr-tree

Issue: #432 (measured) · #304 (the related finding)

## Why

`pull_request` checks out the **merge commit** by default, so `qa-validate`'s `validate` job
ran `make openspec-check` against a tree carrying **every other open change**. `OPENSPEC.md`
is a generated file that every change edits, so the check reported
`[openspec-index] FAIL … (84 active, 0 archived on disk)` on branches whose index was current
when written — measured on #429 and #430 (two different runs, same wording), and earlier on
#423 and #426. A PR could not go green while any sibling merged first, and the "repair" was to
merge the base and regenerate by hand — which the next merge invalidated again.

## What Changes

- **The `validate` job checks out `github.event.pull_request.head.sha`** (falling back to
  `github.sha` on a `push`), so the index — and every other tree-dependent gate — is verified
  against the tree that produced it.
- **`master` is still verified**: this pipeline runs on `push` to master with `github.sha`,
  which is the merge result.
- **`auto-merge` still matches the validated SHA** (`--match-head-commit`), so what merges is
  exactly what was checked.
- **A guard** in `tests/test_workflows.py` asserts the `ref` expression and that
  `fetch-depth: 0` survives (the authorship gate needs the base ref, #317).

## Impact

`.github/workflows/qa-validate.yml` (one `ref:` + its comment), `tests/test_workflows.py`,
this OpenSpec change and the regenerated `OPENSPEC.md`. No target, stage, job or image is
added (`ARCHITECTURE.md` unchanged).

## Not covered

- **Other tree-dependent gates in the same job** (`make lint`, `check_commit_authorship`):
  they were already about the PR's own tree, and this makes that literal for all of them.
- **A change merged into master between a PR's run and its merge.** `auto-merge`'s
  `--match-head-commit` refuses a stale merge and the newer run decides.
